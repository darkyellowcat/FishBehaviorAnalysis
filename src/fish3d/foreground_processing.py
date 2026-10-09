"""S3 video-to-foreground pipeline using the paper's LBAdaptiveSOM baseline."""

import csv
import json
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
import yaml

from fish3d import __version__
from fish3d.lbadaptive_som import ALGORITHM_VERSION, LBAdaptiveSOM, load_som_config
from fish3d.preprocessing import OpenCVPreprocessor
from fish3d.video_config import load_video_config
from fish3d.video_io import OpenCVVideoReader
from fish3d.video_processing import _save_png, _sha256


def segment_video(input_path: Path, config_path: Path, output_dir: Path) -> dict:
    """Save two ROI masks, a full-frame mask, overlays, and final SOM states."""

    video_config = load_video_config(config_path)
    som_config = load_som_config(config_path)
    preprocessor = OpenCVPreprocessor(video_config)
    reader = OpenCVVideoReader(input_path, video_config)
    models = {view: LBAdaptiveSOM(som_config) for view in ("mirror", "real")}
    for name in ("masks/mirror", "masks/real", "masks/full", "overlays"):
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    frame_count = 0
    started = perf_counter()
    with (output_dir / "segmentation.csv").open("w", newline="", encoding="utf-8") as stream:
        columns = (
            "frame_id", "timestamp_s", "timestamp_source", "view", "roi_x", "roi_y",
            "phase", "threshold_squared", "foreground_pixels", "shadow_pixels",
            "background_updates", "elapsed_s", "data_source",
        )
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for frame in reader:
            processed = preprocessor.process(frame)
            full_mask = np.zeros(frame.bgr.shape[:2], dtype=np.uint8)
            stem = f"frame_{frame.frame_id:06d}.png"
            for view_frame in processed.views:
                model = models[view_frame.view]
                before = perf_counter()
                foreground = model.segment(view_frame)
                elapsed = perf_counter() - before
                _save_png(output_dir / "masks" / view_frame.view / stem, foreground.mask)
                height, width = foreground.mask.shape
                full_mask[
                    foreground.roi_y:foreground.roi_y + height,
                    foreground.roi_x:foreground.roi_x + width,
                ] = foreground.mask
                writer.writerow({
                    "frame_id": frame.frame_id, "timestamp_s": frame.timestamp_s,
                    "timestamp_source": frame.timestamp_source, "view": view_frame.view,
                    "roi_x": foreground.roi_x, "roi_y": foreground.roi_y,
                    **model.last_stats, "elapsed_s": elapsed,
                    "data_source": video_config.data_source,
                })
            overlay = processed.median_bgr.copy()
            selected = full_mask != 0
            overlay[selected] = (
                overlay[selected].astype(float) * 0.5 + np.array((0, 0, 255)) * 0.5
            ).astype(np.uint8)
            _save_png(output_dir / "masks/full" / stem, full_mask)
            _save_png(output_dir / "overlays" / stem, overlay)
            frame_count += 1
    if frame_count == 0:
        raise ValueError("video contains no decodable frames")
    for view, model in models.items():
        model.save_model(output_dir / f"background_model_{view}.npz", data_source=video_config.data_source)
    manifest = {
        "stage": "S3", "algorithm": "LBAdaptiveSOM",
        "algorithm_version": ALGORITHM_VERSION, "package_version": __version__,
        "numpy_version": np.__version__, "opencv_version": cv2.__version__,
        "data_source": video_config.data_source,
        "input_video": str(input_path.resolve()), "input_sha256": _sha256(input_path),
        "config_file": str(config_path.resolve()), "config_sha256": _sha256(config_path),
        "config_snapshot": yaml.safe_load(config_path.read_text(encoding="utf-8")),
        "frame_count": frame_count, "nominal_fps": reader.nominal_fps,
        "calibration_applied": preprocessor.calibration is not None,
        "processing_elapsed_s": perf_counter() - started,
        "output_directories": ["masks/mirror", "masks/real", "masks/full", "overlays"],
        "model_files": ["background_model_mirror.npz", "background_model_real.npz"],
        "mask_format": "uint8 PNG: background/shadow 0; foreground 255",
        "limitations": [
            "First-frame foreground is incorporated into the initial background.",
            "Linear HSV weight updates and non-circular shadow hue difference follow the printed equations.",
            "No real-video validation, morphology, centroid extraction, tracking, or reconstruction in S3.",
        ],
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
