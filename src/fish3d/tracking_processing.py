"""S4 centroid/tracking exports layered on the existing S3 pipeline."""

import csv
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fish3d.centroid import ConnectedComponentCentroidExtractor, load_centroid_config
from fish3d.foreground_processing import segment_video
from fish3d.interfaces import ForegroundMask, TrackedDetection
from fish3d.tracking import SingleFishTracker, load_tracking_config, missing_detection
from fish3d.video_processing import _save_png, _sha256

TRACKING_VERSION = "single_fish_pixel_centroid_time_gate_v1"


def _read_png(path: Path, flag: int) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), flag)
    if image is None:
        raise ValueError(f"cannot decode PNG: {path}")
    return image


def _plot_tracks(path: Path, observations: list[TrackedDetection], data_source: str) -> None:
    """Plot separate track segments; NaNs break lines at unobserved frames."""

    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    for axis, view in zip(axes, ("mirror", "real")):
        rows = [item for item in observations if item.detection.view == view]
        identities = sorted({item.fish_id for item in rows if item.fish_id})
        for identity in identities:
            xs = [item.detection.x_px if item.fish_id == identity else np.nan for item in rows]
            ys = [item.detection.y_px if item.fish_id == identity else np.nan for item in rows]
            axis.plot(xs, ys, "o-", markersize=3, label=identity)
        axis.set(title=view, xlabel="Full-frame x (px)", ylabel="Full-frame y (px)")
        axis.invert_yaxis()
        axis.set_aspect("equal", adjustable="datalim")
        axis.grid(True)
        if identities:
            axis.legend()
    figure.suptitle(f"{data_source.upper()} - 2D image tracks")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def track_video(input_path: Path, config_path: Path, output_dir: Path) -> dict:
    """Run S3 then extract/associate each saved view mask using its timestamps.

    The existing S3 artifacts are stored in foreground/. No second decoder pass
    or simulated coordinates are used to produce the measured 2D observations.
    """

    centroid_config = load_centroid_config(config_path)
    tracking_config = load_tracking_config(config_path)
    started = perf_counter()
    foreground_dir = output_dir / "foreground"
    foreground_manifest = segment_video(input_path, config_path, foreground_dir)
    extractors = {
        view: ConnectedComponentCentroidExtractor(centroid_config) for view in ("mirror", "real")
    }
    trackers = {view: SingleFishTracker(view, tracking_config) for view in ("mirror", "real")}
    directories = ("cleaned_masks/mirror", "cleaned_masks/real", "tracking_overlays")
    for name in directories:
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    observations: list[TrackedDetection] = []
    previous_points: dict[str, tuple[str, tuple[int, int]]] = {}
    valid_counts = {view: 0 for view in trackers}
    rejected_counts = {view: 0 for view in trackers}
    columns = (
        "frame_id", "timestamp_s", "view", "x_px", "y_px", "area_px", "is_valid",
        "timestamp_source", "roi_x", "roi_y", "coordinate_unit", "coordinate_frame", "data_source",
    )
    with (
        (foreground_dir / "segmentation.csv").open(newline="", encoding="utf-8") as source,
        (output_dir / "detections.csv").open("w", newline="", encoding="utf-8") as detections_file,
        (output_dir / "tracks_2d.csv").open("w", newline="", encoding="utf-8") as tracks_file,
    ):
        rows = iter(csv.DictReader(source))
        detection_writer = csv.DictWriter(detections_file, fieldnames=(*columns, "candidate_count"))
        tracking_writer = csv.DictWriter(tracks_file, fieldnames=(*columns, "fish_id", "status"))
        detection_writer.writeheader()
        tracking_writer.writeheader()
        for frame_id in range(foreground_manifest["frame_count"]):
            stem = f"frame_{frame_id:06d}.png"
            overlay = _read_png(foreground_dir / "overlays" / stem, cv2.IMREAD_COLOR)
            for _ in range(2):
                row = next(rows)
                view = row["view"]
                mask = ForegroundMask(
                    int(row["frame_id"]), float(row["timestamp_s"]), view,
                    _read_png(foreground_dir / "masks" / view / stem, cv2.IMREAD_GRAYSCALE),
                    int(row["roi_x"]), int(row["roi_y"]),
                )
                extractor = extractors[view]
                detection = extractor.extract(mask)
                if detection is None:
                    detection = missing_detection(mask.frame_id, mask.timestamp_s, view)
                tracker = trackers[view]
                tracked = tracker.update(detection)
                observations.append(tracked)
                metadata = {
                    "timestamp_source": row["timestamp_source"], "roi_x": mask.roi_x, "roi_y": mask.roi_y,
                    "coordinate_unit": "px", "coordinate_frame": "processed_full_frame",
                    "data_source": foreground_manifest["data_source"],
                }
                detection_writer.writerow({
                    **asdict(detection), **metadata, "candidate_count": extractor.last_candidate_count,
                })
                tracking_writer.writerow({
                    **asdict(tracked.detection), **metadata, "fish_id": tracked.fish_id,
                    "status": tracker.last_status,
                })
                _save_png(output_dir / "cleaned_masks" / view / stem, extractor.last_cleaned_mask)
                if tracked.detection.is_valid:
                    valid_counts[view] += 1
                    point = (round(tracked.detection.x_px), round(tracked.detection.y_px))
                    color = (0, 255, 0) if view == "real" else (255, 255, 0)
                    previous = previous_points.get(view)
                    if previous is not None and previous[0] == tracked.fish_id:
                        cv2.line(overlay, previous[1], point, color, 1)
                    cv2.drawMarker(overlay, point, color, cv2.MARKER_CROSS, 9, 1)
                    cv2.putText(overlay, tracked.fish_id, (point[0] + 4, point[1] - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1, cv2.LINE_AA)
                    previous_points[view] = (tracked.fish_id, point)
                else:
                    previous_points.pop(view, None)
                    if tracker.last_status == "rejected":
                        rejected_counts[view] += 1
                        point = (round(detection.x_px), round(detection.y_px))
                        cv2.drawMarker(overlay, point, (0, 255, 255), cv2.MARKER_TILTED_CROSS, 9, 1)
            _save_png(output_dir / "tracking_overlays" / stem, overlay)
    _plot_tracks(output_dir / "tracks_2d.png", observations, foreground_manifest["data_source"])
    manifest = {
        **{key: foreground_manifest[key] for key in (
            "package_version", "numpy_version", "opencv_version", "data_source", "input_video",
            "input_sha256", "config_file", "config_sha256", "config_snapshot", "frame_count",
            "nominal_fps", "calibration_applied",
        )},
        "stage": "S4", "tracking_algorithm_version": TRACKING_VERSION,
        "foreground_manifest": "foreground/run_manifest.json",
        "foreground_manifest_sha256": _sha256(foreground_dir / "run_manifest.json"),
        "valid_tracking_observations": valid_counts, "rejected_observations": rejected_counts,
        "output_directories": list(directories),
        "output_files": ["detections.csv", "tracks_2d.csv", "tracks_2d.png"],
        "processing_elapsed_s": perf_counter() - started,
        "coordinate_unit": "px", "coordinate_frame": "processed_full_frame",
        "limitations": [
            "Single fish per view; largest qualified component may select a reflection or merge fish.",
            "First-frame fish can be incorporated into the SOM background.",
            "View-local IDs denote track segments, not cross-view or verified physical identity.",
            "Time and displacement gates are engineering rules, not paper-specified tracking.",
            "Missing/rejected coordinates remain NaN; no prediction or interpolation is exported.",
            "No real-video validation, dual-view matching, or 3D reconstruction in S4.",
        ],
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return manifest
