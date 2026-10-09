"""Undistortion, median filtering, HSV conversion, and ROI extraction."""

import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import cv2
import numpy as np

from fish3d.interfaces import ProcessedFrame, VideoFrame, ViewFrame
from fish3d.video_config import ROI, VideoConfig


@dataclass(frozen=True, slots=True)
class CameraCalibration:
    camera_matrix: np.ndarray
    distortion_coefficients: np.ndarray
    image_width: int
    image_height: int


def load_calibration(path: Path) -> CameraCalibration:
    """Read camera intrinsics and distortion from a small JSON calibration file."""

    document = json.loads(path.read_text(encoding="utf-8"))
    matrix = np.asarray(document["camera_matrix"], dtype=np.float64)
    coefficients = np.asarray(document["distortion_coefficients"], dtype=np.float64).reshape(-1)
    width, height = int(document["image_width"]), int(document["image_height"])
    if matrix.shape != (3, 3) or coefficients.size not in (4, 5, 8, 12, 14):
        raise ValueError("invalid camera matrix or distortion coefficient shape")
    if not np.isfinite(matrix).all() or not np.isfinite(coefficients).all() or width <= 0 or height <= 0:
        raise ValueError("calibration requires finite values and positive image size")
    if not isfinite(float(matrix[0, 0])) or matrix[0, 0] <= 0 or matrix[1, 1] <= 0:
        raise ValueError("camera focal lengths must be positive")
    return CameraCalibration(matrix, coefficients, width, height)


def _crop(image: np.ndarray, roi: ROI) -> np.ndarray:
    return image[roi.y:roi.y + roi.height, roi.x:roi.x + roi.width].copy()


class OpenCVPreprocessor:
    """Process a full BGR frame before splitting it into HSV view ROIs."""

    def __init__(self, config: VideoConfig) -> None:
        self.config = config
        self.calibration = load_calibration(config.calibration_file) if config.calibration_file else None
        if self.calibration and (
            self.calibration.image_width != config.expected_width
            or self.calibration.image_height != config.expected_height
        ):
            raise ValueError("calibration image size does not match configured video size")

    def process(self, frame: VideoFrame) -> ProcessedFrame:
        if frame.bgr.shape != (self.config.expected_height, self.config.expected_width, 3) or frame.bgr.dtype != np.uint8:
            raise ValueError("frame must be uint8 BGR with the configured full-frame size")
        if self.calibration:
            undistorted = cv2.undistort(
                frame.bgr, self.calibration.camera_matrix, self.calibration.distortion_coefficients
            )
        else:
            undistorted = frame.bgr.copy()
        median = cv2.medianBlur(undistorted, self.config.median_kernel)
        hsv = cv2.cvtColor(median, cv2.COLOR_BGR2HSV)
        mirror, real = self.config.mirror_roi, self.config.real_roi
        views = (
            ViewFrame(frame.frame_id, frame.timestamp_s, "mirror", _crop(hsv, mirror), mirror.x, mirror.y),
            ViewFrame(frame.frame_id, frame.timestamp_s, "real", _crop(hsv, real), real.x, real.y),
        )
        return ProcessedFrame(frame, undistorted, median, hsv, views)

