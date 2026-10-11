"""S5 reconstruction of S4 track tables with explicit ideal-model provenance."""

import csv
import json
from collections import Counter
from math import isnan
from pathlib import Path
from time import perf_counter

import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fish3d import __version__
from fish3d.export import export_trajectory
from fish3d.geometry import GEOMETRY_VERSION, PaperIdealReconstructor, load_geometry_config
from fish3d.interfaces import Detection2D, TrackedDetection
from fish3d.matching import SingleFishDualViewMatcher, load_matching_config
from fish3d.preprocessing import load_calibration
from fish3d.schemas import TrajectoryPoint
from fish3d.tracking import missing_detection
from fish3d.video_config import VideoConfig, load_video_config
from fish3d.video_processing import _sha256


def _read_frames(path: Path, config: VideoConfig) -> list[dict[str, dict]]:
    """Read ordered full-frame S4 rows, retaining frames with just one view."""

    frames: list[dict[str, dict]] = []
    previous_frame = -1
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["data_source"] != config.data_source:
                raise ValueError("input track data_source does not match configuration")
            if row["coordinate_unit"] != "px" or row["coordinate_frame"] != "processed_full_frame":
                raise ValueError("input tracks require px in processed_full_frame coordinates")
            view = row["view"]
            if view not in ("real", "mirror"):
                raise ValueError("input view must be real or mirror")
            roi = config.real_roi if view == "real" else config.mirror_roi
            if (int(row["roi_x"]), int(row["roi_y"])) != (roi.x, roi.y):
                raise ValueError("input ROI origin does not match configuration")
            frame_id = int(row["frame_id"])
            if frame_id < 0 or frame_id < previous_frame:
                raise ValueError("input frames must be nonnegative and ordered")
            if frame_id != previous_frame:
                frames.append({})
                previous_frame = frame_id
            if view in frames[-1]:
                raise ValueError("duplicate view in one frame")
            validity = row["is_valid"].lower()
            if validity not in ("true", "false"):
                raise ValueError("is_valid must be true or false")
            detection = Detection2D(
                frame_id, float(row["timestamp_s"]), view, float(row["x_px"]), float(row["y_px"]),
                int(row["area_px"]), validity == "true",
            )
            if detection.is_valid and not (
                roi.x <= detection.x_px < roi.x + roi.width
                and roi.y <= detection.y_px < roi.y + roi.height
            ):
                raise ValueError("valid point is outside its declared full-frame ROI")
            if not detection.is_valid and not (
                isnan(detection.x_px) and isnan(detection.y_px) and detection.area_px == 0
            ):
                raise ValueError("invalid input detection requires NaN coordinates and zero area")
            frames[-1][view] = {
                "tracked": TrackedDetection(detection, row["fish_id"]),
                "timestamp_source": row["timestamp_source"],
            }
    if not frames:
        raise ValueError("input track table is empty")
    return frames


def _plot_reconstruction(path: Path, points: list[TrajectoryPoint], data_source: str) -> None:
    """Break 3D paths at invalid points and changes of paired track identity."""

    figure = plt.figure(figsize=(8, 6))
    axis = figure.add_subplot(111, projection="3d")
    identities = sorted({point.fish_id for point in points if point.is_valid})
    for identity in identities:
        coordinates = [
            (point.X, point.Y, point.Z) if point.fish_id == identity else (np.nan,) * 3
            for point in points
        ]
        array = np.asarray(coordinates)
        axis.plot(array[:, 0], array[:, 1], array[:, 2], "o-", markersize=3, label=identity)
    unit = points[0].coordinate_unit
    axis.set(
        xlabel=f"X ({unit})", ylabel=f"Y ({unit})", zlabel=f"Z ({unit})",
        title=f"{data_source.upper()} - unverified ideal-model reconstruction",
    )
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def reconstruct_tracks(input_path: Path, config_path: Path, output_dir: Path) -> dict:
    """Match a single-fish S4 table and save one valid/invalid 3D row per frame."""

    started = perf_counter()
    video_config = load_video_config(config_path)
    geometry_config = load_geometry_config(config_path)
    matcher = SingleFishDualViewMatcher(load_matching_config(config_path))
    model = PaperIdealReconstructor(geometry_config, video_config.data_source)
    camera_metadata = None
    if video_config.calibration_file is not None:
        calibration = load_calibration(video_config.calibration_file)
        if (calibration.image_width, calibration.image_height) != (
            video_config.expected_width, video_config.expected_height,
        ):
            raise ValueError("calibration image size does not match configured video size")
        camera_metadata = {
            "file": str(video_config.calibration_file.resolve()),
            "sha256": _sha256(video_config.calibration_file),
            "used_for_metric_reconstruction": False,
        }
    frames = _read_frames(input_path, video_config)
    points: list[TrajectoryPoint] = []
    matching_rows = []
    last_identity = "unassigned"
    previous_time = -1.0
    for frame in frames:
        reference = frame.get("real", frame.get("mirror"))["tracked"].detection
        real = frame.get("real", {}).get("tracked")
        mirror = frame.get("mirror", {}).get("tracked")
        if real is None:
            real = TrackedDetection(missing_detection(reference.frame_id, reference.timestamp_s, "real"), "")
        if mirror is None:
            mirror = TrackedDetection(missing_detection(reference.frame_id, reference.timestamp_s, "mirror"), "")
        matched = matcher.match(real, mirror)
        if reference.timestamp_s <= previous_time:
            raise ValueError("frame timestamps must increase strictly")
        previous_time = reference.timestamp_s
        if matched is not None:
            point = model.reconstruct(*matched)
            last_identity = point.fish_id
        else:
            point = model.invalid_point(reference.frame_id, reference.timestamp_s, last_identity)
        points.append(point)
        matching_rows.append({
            "frame_id": point.frame_id, "timestamp_s": point.timestamp_s,
            "real_timestamp_s": real.detection.timestamp_s if "real" in frame else "NaN",
            "mirror_timestamp_s": mirror.detection.timestamp_s if "mirror" in frame else "NaN",
            "real_timestamp_source": frame.get("real", {}).get("timestamp_source", ""),
            "mirror_timestamp_source": frame.get("mirror", {}).get("timestamp_source", ""),
            "real_present": "real" in frame, "mirror_present": "mirror" in frame,
            "real_track_id": real.fish_id, "mirror_track_id": mirror.fish_id,
            "fish_id": point.fish_id, "is_matched": matched is not None,
            "status": matcher.last_status if len(frame) == 2 else "missing_view",
            "y_disparity_px": matcher.last_y_disparity_px,
            "data_source": video_config.data_source,
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "matches.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(matching_rows[0]))
        writer.writeheader()
        writer.writerows(matching_rows)
    export_trajectory(output_dir / "trajectory_3d.csv", points)
    _plot_reconstruction(output_dir / "trajectory_3d.png", points, video_config.data_source)
    manifest = {
        "stage": "S5", "package_version": __version__, "geometry_algorithm_version": GEOMETRY_VERSION,
        "numpy_version": np.__version__, "matplotlib_version": matplotlib.__version__,
        "data_source": video_config.data_source,
        "input_tracks": str(input_path.resolve()), "input_tracks_sha256": _sha256(input_path),
        "config_file": str(config_path.resolve()), "config_sha256": _sha256(config_path),
        "config_snapshot": yaml.safe_load(config_path.read_text(encoding="utf-8")),
        "frame_count": len(points), "valid_point_count": sum(point.is_valid for point in points),
        "matching_status_counts": dict(Counter(row["status"] for row in matching_rows)),
        "coordinate_unit": geometry_config.coordinate_unit, "coordinate_frame": geometry_config.coordinate_frame,
        "configured_camera_calibration": camera_metadata,
        "upstream_undistortion_status": "not_proven_by_track_csv",
        "metric_calibration_applied": False, "geometry_validated_on_real_data": False,
        "processing_elapsed_s": perf_counter() - started,
        "output_files": ["matches.csv", "trajectory_3d.csv", "trajectory_3d.png"],
        "limitations": [
            "Ideal formula only; image coordinates are not physical millimeters or tank coordinates.",
            "Synchronized single-fish matching and aligned image-y coordinates are assumptions.",
            "a is a separately configured full-frame geometric reference, not automatically the ROI boundary.",
            "Paired IDs refer to assumed 2D segment correspondence, not verified physical identity.",
            "No calibrated camera/mirror ray geometry, perspective correction, or water/glass refraction model.",
            "Changing the angle evaluates the printed formula; apparatus accuracy is unverified.",
        ],
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return manifest
