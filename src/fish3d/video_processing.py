"""Save traceable S2 preprocessing outputs without foreground detection."""

import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import yaml

from fish3d import __version__
from fish3d.preprocessing import OpenCVPreprocessor
from fish3d.video_config import load_video_config
from fish3d.video_io import OpenCVVideoReader


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_png(path: Path, image: np.ndarray) -> None:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise OSError(f"failed to write image: {path}")
    path.write_bytes(encoded.tobytes())


def preprocess_video(input_path: Path, config_path: Path, output_dir: Path) -> dict:
    """Read a video and save full-frame stages plus both view ROIs."""

    config = load_video_config(config_path)
    preprocessor = OpenCVPreprocessor(config)
    reader = OpenCVVideoReader(input_path, config)
    stage_dirs = {
        name: output_dir / name
        for name in (
            "undistorted_bgr", "median_bgr", "full_hsv",
            "mirror_hsv", "real_hsv", "mirror_preview", "real_preview",
        )
    }
    for directory in stage_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    counts = {"decoder": 0, "fps_fallback": 0}
    frame_count = 0
    with (output_dir / "frames.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=(
            "frame_id", "timestamp_s", "timestamp_source", "data_source",
            "mirror_roi_x", "mirror_roi_y", "real_roi_x", "real_roi_y",
        ))
        writer.writeheader()
        for frame in reader:
            processed = preprocessor.process(frame)
            stem = f"frame_{frame.frame_id:06d}"
            _save_png(stage_dirs["undistorted_bgr"] / f"{stem}.png", processed.undistorted_bgr)
            _save_png(stage_dirs["median_bgr"] / f"{stem}.png", processed.median_bgr)
            np.save(stage_dirs["full_hsv"] / f"{stem}.npy", processed.full_hsv)
            for view_frame in processed.views:
                np.save(stage_dirs[f"{view_frame.view}_hsv"] / f"{stem}.npy", view_frame.image)
                preview = cv2.cvtColor(view_frame.image, cv2.COLOR_HSV2BGR)
                _save_png(stage_dirs[f"{view_frame.view}_preview"] / f"{stem}.png", preview)
            writer.writerow({
                "frame_id": frame.frame_id,
                "timestamp_s": frame.timestamp_s,
                "timestamp_source": frame.timestamp_source,
                "data_source": frame.data_source,
                "mirror_roi_x": config.mirror_roi.x,
                "mirror_roi_y": config.mirror_roi.y,
                "real_roi_x": config.real_roi.x,
                "real_roi_y": config.real_roi.y,
            })
            counts[frame.timestamp_source] += 1
            frame_count += 1
    if frame_count == 0:
        raise ValueError("video contains no decodable frames")

    manifest = {
        "stage": "S2",
        "algorithm_version": __version__,
        "data_source": config.data_source,
        "input_video": str(input_path.resolve()),
        "input_sha256": _sha256(input_path),
        "config_file": str(config_path.resolve()),
        "config_sha256": _sha256(config_path),
        "config_snapshot": yaml.safe_load(config_path.read_text(encoding="utf-8")),
        "frame_count": frame_count,
        "nominal_fps": reader.nominal_fps,
        "timestamp_sources": counts,
        "calibration_applied": preprocessor.calibration is not None,
        "hsv_format": "OpenCV uint8 HSV in .npy: H 0..179, S/V 0..255",
        "output_directories": list(stage_dirs),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest

