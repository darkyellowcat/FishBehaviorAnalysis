"""OpenCV video input and deterministic synthetic S2 video generation."""

from math import isfinite, pi, sin
from pathlib import Path
from typing import Iterator, Literal

import cv2
import numpy as np

from fish3d.interfaces import VideoFrame
from fish3d.video_config import ROI, VideoConfig


class OpenCVVideoReader:
    """Yield BGR frames with decoder timestamps or an explicit FPS fallback."""

    def __init__(self, path: Path, config: VideoConfig) -> None:
        self.path = path
        self.config = config
        self.nominal_fps: float | None = None

    def __iter__(self) -> Iterator[VideoFrame]:
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        capture = cv2.VideoCapture(str(self.path))
        if not capture.isOpened():
            raise ValueError(f"cannot open video: {self.path}")
        try:
            reported_fps = float(capture.get(cv2.CAP_PROP_FPS))
            self.nominal_fps = reported_fps if isfinite(reported_fps) and reported_fps > 0 else self.config.fps_fallback
            frame_id = 0
            previous_time = -1.0
            while True:
                success, bgr = capture.read()
                if not success:
                    break
                if bgr.shape[:2] != (self.config.expected_height, self.config.expected_width):
                    raise ValueError("video frame size does not match configured expected size")
                decoder_time = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
                if isfinite(decoder_time) and decoder_time >= 0 and decoder_time > previous_time:
                    timestamp_s = decoder_time
                    timestamp_source: Literal["decoder", "fps_fallback"] = "decoder"
                else:
                    timestamp_s = max(frame_id / self.nominal_fps, previous_time + 1 / self.nominal_fps)
                    timestamp_source = "fps_fallback"
                yield VideoFrame(frame_id, timestamp_s, bgr, timestamp_source, self.config.data_source)
                previous_time = timestamp_s
                frame_id += 1
        finally:
            capture.release()


def _fish_center(roi: ROI, offset: int) -> tuple[int, int]:
    return roi.x + roi.width // 2 + offset, roi.y + roi.height // 2


def generate_synthetic_video(path: Path, config: VideoConfig) -> None:
    """Write a labeled synthetic AVI with one simple ellipse in each view."""

    synthetic = config.synthetic_video
    if config.data_source != "synthetic" or synthetic is None:
        raise ValueError("synthetic video generation requires a synthetic configuration")
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*synthetic.codec)
    writer = cv2.VideoWriter(
        str(path), fourcc, synthetic.fps,
        (config.expected_width, config.expected_height),
    )
    if not writer.isOpened():
        raise ValueError(f"cannot create synthetic video: {path}")
    try:
        for frame_id in range(synthetic.frame_count):
            image = np.empty((config.expected_height, config.expected_width, 3), dtype=np.uint8)
            image[:] = synthetic.background_bgr
            offset = round(synthetic.horizontal_motion_px * sin(2 * pi * frame_id / synthetic.frame_count))
            if frame_id >= synthetic.background_only_frames:
                cv2.ellipse(image, _fish_center(config.mirror_roi, -offset), synthetic.fish_axes_px, 0, 0, 360, synthetic.mirror_fish_bgr, -1)
                cv2.ellipse(image, _fish_center(config.real_roi, offset), synthetic.fish_axes_px, 0, 0, 360, synthetic.real_fish_bgr, -1)
            cv2.putText(image, "SYNTHETIC", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            writer.write(image)
    finally:
        writer.release()

