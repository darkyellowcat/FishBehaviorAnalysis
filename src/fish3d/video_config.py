"""Validated configuration for video preprocessing and the synthetic fixture."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Literal

import yaml


@dataclass(frozen=True, slots=True)
class ROI:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("ROI origin must be nonnegative and size positive")

    def fits(self, width: int, height: int) -> bool:
        return self.x + self.width <= width and self.y + self.height <= height


@dataclass(frozen=True, slots=True)
class SyntheticVideoConfig:
    frame_count: int
    fps: float
    codec: str
    fish_axes_px: tuple[int, int]
    horizontal_motion_px: int
    background_bgr: tuple[int, int, int]
    mirror_fish_bgr: tuple[int, int, int]
    real_fish_bgr: tuple[int, int, int]

    def __post_init__(self) -> None:
        if self.frame_count < 2 or not isfinite(self.fps) or self.fps <= 0:
            raise ValueError("synthetic frame_count and fps must be positive")
        if len(self.codec) != 4:
            raise ValueError("video codec must be a four-character code")
        if len(self.fish_axes_px) != 2 or min(self.fish_axes_px) <= 0 or self.horizontal_motion_px < 0:
            raise ValueError("synthetic fish size and movement must be valid")
        for color in (self.background_bgr, self.mirror_fish_bgr, self.real_fish_bgr):
            if len(color) != 3 or any(channel < 0 or channel > 255 for channel in color):
                raise ValueError("BGR colors require three 0..255 values")


@dataclass(frozen=True, slots=True)
class VideoConfig:
    data_source: Literal["synthetic", "experimental"]
    expected_width: int
    expected_height: int
    fps_fallback: float
    median_kernel: int
    calibration_file: Path | None
    mirror_roi: ROI
    real_roi: ROI
    synthetic_video: SyntheticVideoConfig | None

    def __post_init__(self) -> None:
        if self.data_source not in ("synthetic", "experimental"):
            raise ValueError("data_source must be synthetic or experimental")
        if self.expected_width <= 0 or self.expected_height <= 0:
            raise ValueError("expected video size must be positive")
        if not isfinite(self.fps_fallback) or self.fps_fallback <= 0:
            raise ValueError("fps_fallback must be positive")
        if self.median_kernel < 3 or self.median_kernel % 2 == 0:
            raise ValueError("median_kernel must be odd and at least 3")
        if not self.mirror_roi.fits(self.expected_width, self.expected_height):
            raise ValueError("mirror ROI exceeds expected frame size")
        if not self.real_roi.fits(self.expected_width, self.expected_height):
            raise ValueError("real ROI exceeds expected frame size")
        mirror, real = self.mirror_roi, self.real_roi
        if mirror.x < real.x + real.width and real.x < mirror.x + mirror.width and mirror.y < real.y + real.height and real.y < mirror.y + mirror.height:
            raise ValueError("real and mirror ROIs must not overlap")
        if self.synthetic_video is not None:
            axes = self.synthetic_video.fish_axes_px
            for roi in (mirror, real):
                if roi.width <= 2 * (axes[0] + self.synthetic_video.horizontal_motion_px) or roi.height <= 2 * axes[1]:
                    raise ValueError("synthetic fish does not fit within an ROI")


def load_video_config(path: Path) -> VideoConfig:
    """Load an S2 YAML file; relative calibration paths use the config directory."""

    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict):
        raise ValueError("video configuration must be a mapping")
    video = document["video"]
    preprocessing = document["preprocessing"]
    rois = document["rois"]
    calibration_name = preprocessing.get("calibration_file")
    calibration_file = None if calibration_name is None else Path(calibration_name)
    if calibration_file is not None and not calibration_file.is_absolute():
        calibration_file = path.parent / calibration_file
    synthetic = document.get("synthetic_video")
    return VideoConfig(
        data_source=document["data_source"],
        expected_width=video["expected_width"],
        expected_height=video["expected_height"],
        fps_fallback=video["fps_fallback"],
        median_kernel=preprocessing["median_kernel"],
        calibration_file=calibration_file,
        mirror_roi=ROI(**rois["mirror"]),
        real_roi=ROI(**rois["real"]),
        synthetic_video=None if synthetic is None else SyntheticVideoConfig(
            frame_count=synthetic["frame_count"],
            fps=synthetic["fps"],
            codec=synthetic["codec"],
            fish_axes_px=tuple(synthetic["fish_axes_px"]),
            horizontal_motion_px=synthetic["horizontal_motion_px"],
            background_bgr=tuple(synthetic["background_bgr"]),
            mirror_fish_bgr=tuple(synthetic["mirror_fish_bgr"]),
            real_fish_bgr=tuple(synthetic["real_fish_bgr"]),
        ),
    )

