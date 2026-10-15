"""Bounded multi-fish 2D previews using the paper SOM and existing preprocessing."""

import csv
import json
from collections import Counter
from contextlib import closing
from dataclasses import asdict, dataclass
from itertools import islice
from math import isfinite
from pathlib import Path
from time import perf_counter

import cv2
import matplotlib
import numpy as np
import scipy
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fish3d import __version__
from fish3d.centroid import ConnectedComponentCentroidExtractor, load_centroid_config
from fish3d.interfaces import Detection2D, ViewFrame
from fish3d.lbadaptive_som import ALGORITHM_VERSION, LBAdaptiveSOM, load_som_config
from fish3d.multi_tracking import MultiFishTracker, load_multi_tracking_config
from fish3d.preprocessing import OpenCVPreprocessor
from fish3d.video_config import ROI, load_video_config
from fish3d.video_io import OpenCVVideoReader
from fish3d.video_processing import _save_png, _sha256


@dataclass(frozen=True, slots=True)
class MultiProcessingConfig:
    view: str
    processing_scale: float
    max_frames: int
    roi_status: str

    def __post_init__(self) -> None:
        if self.view not in ("real", "mirror"):
            raise ValueError("view must be real or mirror")
        if not isfinite(self.processing_scale) or not 0 < self.processing_scale <= 1:
            raise ValueError("processing_scale must be in (0, 1]")
        if not isinstance(self.max_frames, int) or self.max_frames < 1:
            raise ValueError("max_frames must be a positive integer")
        if not self.roi_status:
            raise ValueError("roi_status must describe how the ROI was obtained")


def restore_coordinates(detection: Detection2D, roi: ROI, scale_x: float, scale_y: float) -> Detection2D:
    """Map resized local pixel centers into original processed full-frame pixels.

    Area is an approximate full-resolution equivalent, not a measured contour
    at original resolution. The scaled mask's area thresholds stay in local px.
    """

    return Detection2D(
        detection.frame_id, detection.timestamp_s, detection.view,
        roi.x + (detection.x_px + 0.5) / scale_x - 0.5,
        roi.y + (detection.y_px + 0.5) / scale_y - 0.5,
        round(detection.area_px / (scale_x * scale_y)), True,
    )


def _plot_observations(path: Path, observations: list, source: str, view: str) -> None:
    figure, axis = plt.subplots(figsize=(8, 6))
    identities = sorted({item.tracked.fish_id for item in observations})
    for identity in identities:
        points = [item.tracked.detection for item in observations if item.tracked.fish_id == identity]
        axis.plot([point.x_px for point in points], [point.y_px for point in points], ".-", label=identity)
    axis.set(title=f"{source.upper()} - {view} 2D segments; identities unverified",
             xlabel="Processed full-frame x (px)", ylabel="Processed full-frame y (px)")
    axis.invert_yaxis()
    axis.set_aspect("equal", adjustable="datalim")
    axis.grid(alpha=0.3)
    if identities:
        axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def track_multi_video(input_path: Path, config_path: Path, output_dir: Path) -> dict:
    """Process one configured view and bounded consecutive frames, without 3D claims."""

    document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    processing = MultiProcessingConfig(**document["multi_processing"])
    config = load_video_config(config_path)
    tracking_config = load_multi_tracking_config(config_path)
    preprocessor = OpenCVPreprocessor(config)
    roi = config.real_roi if processing.view == "real" else config.mirror_roi
    width = max(1, round(roi.width * processing.processing_scale))
    height = max(1, round(roi.height * processing.processing_scale))
    scale_x, scale_y = width / roi.width, height / roi.height
    som = LBAdaptiveSOM(load_som_config(config_path))
    extractor = ConnectedComponentCentroidExtractor(load_centroid_config(config_path))
    tracker = MultiFishTracker(processing.view, tracking_config)
    reader = OpenCVVideoReader(input_path, config)
    for name in ("scaled_masks", "cleaned_masks", "tracking_overlays"):
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    metadata = {"coordinate_unit": "px", "coordinate_frame": "processed_full_frame",
                "data_source": config.data_source, "roi_x": roi.x, "roi_y": roi.y}
    detection_columns = ("frame_id", "timestamp_s", "view", "x_px", "y_px", "area_px", "is_valid",
                         *metadata.keys(), "timestamp_source")
    frame_columns = ("frame_id", "timestamp_s", "timestamp_source", "view", "data_source", "phase",
                     "candidate_count", "area_candidate_count", "shape_rejected_count", "tentative_candidate_count",
                     "valid_track_count", "missing_track_count", "lost_track_count",
                     "expected_fish_count", "scale_x", "scale_y")
    observations, frame_rows = [], []
    started = perf_counter()
    with (
        closing(iter(reader)) as frames,
        (output_dir / "detections.csv").open("w", encoding="utf-8", newline="") as detection_file,
        (output_dir / "tracks_2d.csv").open("w", encoding="utf-8", newline="") as track_file,
        (output_dir / "frames.csv").open("w", encoding="utf-8", newline="") as frame_file,
        (output_dir / "components.csv").open("w", encoding="utf-8", newline="") as component_file,
    ):
        detection_writer = csv.DictWriter(detection_file, fieldnames=(*detection_columns, "detection_index", "status"))
        track_writer = csv.DictWriter(track_file, fieldnames=(*detection_columns, "fish_id", "status"))
        frame_writer = csv.DictWriter(frame_file, fieldnames=frame_columns)
        component_writer = csv.DictWriter(component_file, fieldnames=(
            "frame_id", "timestamp_s", "view", "component_label", "x_mask_px", "y_mask_px", "area_mask_px",
            "axis_ratio", "shape_accepted", "data_source",
        ))
        for writer in (detection_writer, track_writer, frame_writer, component_writer):
            writer.writeheader()
        for frame in islice(frames, processing.max_frames):
            processed = preprocessor.process(frame)
            crop = processed.median_bgr[roi.y:roi.y + roi.height, roi.x:roi.x + roi.width]
            bgr = cv2.resize(crop, (width, height), interpolation=cv2.INTER_AREA)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            local = ViewFrame(frame.frame_id, frame.timestamp_s, processing.view, hsv, 0, 0)
            mask = som.segment(local)
            candidates = extractor.extract_all(mask)
            for feature in extractor.last_component_features:
                component_writer.writerow({
                    "frame_id": frame.frame_id, "timestamp_s": frame.timestamp_s, "view": processing.view,
                    "component_label": feature["component_label"], "x_mask_px": feature["x_px"],
                    "y_mask_px": feature["y_px"], "area_mask_px": feature["area_px"],
                    "axis_ratio": feature["axis_ratio"], "shape_accepted": feature["shape_accepted"],
                    "data_source": config.data_source,
                })
            detections = [restore_coordinates(item, roi, scale_x, scale_y) for item in candidates]
            tracked = tracker.update(frame.frame_id, frame.timestamp_s, detections)
            observations.extend(tracked)
            provenance = {**metadata, "timestamp_source": frame.timestamp_source}
            for index, detection in enumerate(detections):
                detection_writer.writerow({**asdict(detection), **provenance, "detection_index": index,
                                           "status": tracker.last_detection_statuses[index]})
            for item in tracked:
                track_writer.writerow({**asdict(item.tracked.detection), **provenance,
                                       "fish_id": item.tracked.fish_id, "status": item.status})
            valid_count = sum(item.tracked.detection.is_valid for item in tracked)
            row = {"frame_id": frame.frame_id, "timestamp_s": frame.timestamp_s,
                   "timestamp_source": frame.timestamp_source, "view": processing.view,
                   "data_source": config.data_source, "phase": som.last_stats["phase"],
                   "candidate_count": len(candidates), "valid_track_count": valid_count,
                   "area_candidate_count": extractor.last_area_candidate_count,
                   "shape_rejected_count": extractor.last_shape_rejected_count,
                   "tentative_candidate_count": tracker.last_detection_statuses.count("tentative"),
                   "missing_track_count": sum(item.status in ("missing", "occluded") for item in tracked),
                   "lost_track_count": sum(item.status == "lost" for item in tracked),
                   "expected_fish_count": tracking_config.expected_fish_count,
                   "scale_x": scale_x, "scale_y": scale_y}
            frame_rows.append(row)
            frame_writer.writerow(row)
            stem = f"frame_{frame.frame_id:06d}.png"
            _save_png(output_dir / "scaled_masks" / stem, mask.mask)
            _save_png(output_dir / "cleaned_masks" / stem, extractor.last_cleaned_mask)
            overlay = processed.undistorted_bgr.copy()
            cv2.rectangle(overlay, (roi.x, roi.y), (roi.x + roi.width - 1, roi.y + roi.height - 1), (0, 165, 255), 2)
            for detection, status in zip(detections, tracker.last_detection_statuses):
                if status not in ("tracked", "initialized"):
                    cv2.drawMarker(overlay, (round(detection.x_px), round(detection.y_px)), (128, 128, 128),
                                   cv2.MARKER_TILTED_CROSS, 7, 1)
            for item in tracked:
                detection = item.tracked.detection
                if detection.is_valid:
                    identifier = int(item.tracked.fish_id.rsplit("_", 1)[1])
                    color = tuple(int(channel) for channel in cv2.cvtColor(
                        np.array([[[identifier * 37 % 180, 220, 255]]], dtype=np.uint8), cv2.COLOR_HSV2BGR)[0, 0])
                    position = (round(detection.x_px), round(detection.y_px))
                    cv2.drawMarker(overlay, position, color, cv2.MARKER_CROSS, 9, 2)
                    cv2.putText(overlay, item.tracked.fish_id, (position[0] + 4, position[1] - 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
            cv2.putText(overlay, f"{config.data_source.upper()} - {processing.view} 2D preview; IDs unverified",
                        (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(overlay, f"frame={frame.frame_id} candidates={len(detections)} observed_tracks={valid_count}",
                        (8, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            _save_png(output_dir / "tracking_overlays" / stem, overlay)
    if not frame_rows:
        raise ValueError("video contains no readable frames")
    _plot_observations(output_dir / "tracks_2d.png", observations, config.data_source, processing.view)
    som.save_model(output_dir / "som_model.npz", data_source=config.data_source)
    manifest = {
        "stage": "multi_fish_2d_preview", "algorithm_version": "multi_prediction_assignment_confirm_v2",
        "effective_tracking_config": asdict(tracking_config),
        "som_algorithm_version": ALGORITHM_VERSION, "package_version": __version__,
        "centroid_algorithm_version": "components_axis_moments_v2",
        "effective_centroid_config": asdict(extractor.config),
        "numpy_version": np.__version__, "scipy_version": scipy.__version__, "opencv_version": cv2.__version__,
        "data_source": config.data_source, "view": processing.view,
        "input_video": str(input_path.resolve()), "input_sha256": _sha256(input_path),
        "config_file": str(config_path.resolve()), "config_sha256": _sha256(config_path), "config_snapshot": document,
        "frame_count": len(frame_rows), "start_s": frame_rows[0]["timestamp_s"], "end_s": frame_rows[-1]["timestamp_s"],
        "nominal_fps": reader.nominal_fps, "calibration_applied": preprocessor.calibration is not None,
        "timestamp_source_counts": dict(Counter(row["timestamp_source"] for row in frame_rows)),
        "expected_fish_count": tracking_config.expected_fish_count,
        "candidate_count_histogram": dict(Counter(row["candidate_count"] for row in frame_rows)),
        "area_candidate_total": sum(row["area_candidate_count"] for row in frame_rows),
        "shape_rejected_total": sum(row["shape_rejected_count"] for row in frame_rows),
        "tentative_detection_total": sum(row["tentative_candidate_count"] for row in frame_rows),
        "valid_track_count_histogram": dict(Counter(row["valid_track_count"] for row in frame_rows)),
        "track_status_counts": dict(Counter(item.status for item in observations)),
        "coordinate_unit": "px", "coordinate_frame": "processed_full_frame",
        "scaled_mask_size": [width, height], "effective_scale_xy": [scale_x, scale_y], "roi_status": processing.roi_status,
        "physical_identity_validated": False, "cross_view_matching_applied": False,
        "reconstruction_applied": False, "accuracy_validated_with_manual_labels": False,
        "output_files": ["detections.csv", "tracks_2d.csv", "frames.csv", "components.csv", "tracks_2d.png", "som_model.npz", "run_manifest.json"],
        "output_directories": ["scaled_masks", "cleaned_masks", "tracking_overlays"],
        "processing_elapsed_s": perf_counter() - started,
        "limitations": [
            "Single configured view and bounded consecutive preview only, not full-video acceptance.",
            "Known population count caps active segments, never forces five observed fish.",
            "Optional birth confirmation delays observations and may reject briefly visible real fish; no backfill.",
            "Candidates may be bubbles/reflections; selected segments are not confirmed physical fish identities.",
            "Optional shape filtering may reject head-on/curled fish and does not prove bubble/fish identity.",
            "Merged-area exclusion is an engineering heuristic and does not split touching fish.",
            "After long gaps, IDs restart; crossing/occlusion identity is unverified without appearance/labels.",
            "SOM first-frame initialization can absorb fish; lighting changes and mirror motion remain unresolved.",
            "Resize changes segmentation and centroid precision; areas are approximate full-resolution equivalents.",
            "Multi-fish 3D correspondence and behavior CSV ingestion still require separate adaptation.",
        ],
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def generate_multi_video(path: Path, config_path: Path, truth_path: Path) -> None:
    """Construct labeled multi-fish imagery and independent fixture coordinates."""

    document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config = load_video_config(config_path)
    if config.data_source != "synthetic":
        raise ValueError("multi-tracking-demo requires data_source=synthetic")
    fixture = document["synthetic_multi_video"]
    if len(fixture["fish"]) != load_multi_tracking_config(config_path).expected_fish_count:
        raise ValueError("synthetic fixture population must match expected_fish_count")
    roi = config.real_roi
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*fixture["codec"]), fixture["fps"],
                             (config.expected_width, config.expected_height))
    if not writer.isOpened():
        raise ValueError(f"cannot create synthetic video: {path}")
    try:
        with truth_path.open("w", encoding="utf-8", newline="") as stream:
            columns = ("frame_id", "timestamp_s", "fixture_id", "x_px", "y_px", "is_valid", "data_source")
            truth_writer = csv.DictWriter(stream, fieldnames=columns)
            truth_writer.writeheader()
            for frame_id in range(fixture["frame_count"]):
                image = np.full((config.expected_height, config.expected_width, 3), fixture["background_bgr"], dtype=np.uint8)
                for index, fish in enumerate(fixture["fish"]):
                    valid = frame_id >= fixture["background_only_frames"] and frame_id not in fish["missing_frame_ids"]
                    elapsed = max(0, frame_id - fixture["background_only_frames"]) / fixture["fps"]
                    x, y = (round(fish["start_px"][axis] + fish["velocity_px_s"][axis] * elapsed) for axis in (0, 1))
                    if valid:
                        ax, ay = fixture["fish_axes_px"]
                        if not (ax <= x < roi.width - ax and ay <= y < roi.height - ay):
                            raise ValueError("synthetic fish must stay within real ROI")
                        cv2.ellipse(image, (roi.x + x, roi.y + y), (ax, ay), 0, 0, 360, tuple(fixture["fish_bgr"]), -1)
                    truth_writer.writerow({"frame_id": frame_id, "timestamp_s": frame_id / fixture["fps"],
                                           "fixture_id": f"synthetic_{index + 1:02d}", "x_px": roi.x + x if valid else "NaN",
                                           "y_px": roi.y + y if valid else "NaN", "is_valid": str(valid).lower(), "data_source": "synthetic"})
                cv2.putText(image, "SYNTHETIC", (roi.x + roi.width + 2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                            (255, 255, 255), 1, cv2.LINE_AA)
                writer.write(image)
    finally:
        writer.release()
