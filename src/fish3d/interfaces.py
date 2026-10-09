"""S0 contracts for later stages; these protocols perform no image processing."""

from dataclasses import dataclass
from typing import Iterator, Literal, Protocol, Sequence

import numpy as np

from fish3d.schemas import TrajectoryPoint, View


@dataclass(frozen=True, slots=True)
class VideoFrame:
    frame_id: int
    timestamp_s: float
    bgr: np.ndarray
    timestamp_source: Literal["decoder", "fps_fallback"]
    data_source: Literal["synthetic", "experimental"]


@dataclass(frozen=True, slots=True)
class ViewFrame:
    frame_id: int
    timestamp_s: float
    view: View
    image: np.ndarray
    roi_x: int  # offset from ROI-local coordinates to the full frame
    roi_y: int


@dataclass(frozen=True, slots=True)
class ProcessedFrame:
    frame: VideoFrame
    undistorted_bgr: np.ndarray
    median_bgr: np.ndarray
    full_hsv: np.ndarray
    views: tuple[ViewFrame, ViewFrame]


@dataclass(frozen=True, slots=True)
class ForegroundMask:
    frame_id: int
    timestamp_s: float
    view: View
    mask: np.ndarray  # uint8, 0/255; coordinates local to the view ROI
    roi_x: int
    roi_y: int


@dataclass(frozen=True, slots=True)
class Detection2D:
    frame_id: int
    timestamp_s: float
    view: View
    x_px: float  # full-frame coordinates
    y_px: float
    area_px: int
    is_valid: bool


@dataclass(frozen=True, slots=True)
class TrackedDetection:
    detection: Detection2D
    fish_id: str


@dataclass(frozen=True, slots=True)
class BehaviorEvent:
    fish_id: str
    behavior: str
    start_s: float
    end_s: float


class VideoSource(Protocol):
    def __iter__(self) -> Iterator[VideoFrame]: ...


class FramePreprocessor(Protocol):
    def process(self, frame: VideoFrame) -> ProcessedFrame: ...


class ForegroundSegmenter(Protocol):
    def segment(self, view_frame: ViewFrame) -> ForegroundMask: ...


class CentroidExtractor(Protocol):
    def extract(self, mask: ForegroundMask) -> Detection2D | None: ...


class DetectionTracker(Protocol):
    def track(self, detections: Sequence[Detection2D]) -> Sequence[TrackedDetection]: ...


class DualViewMatcher(Protocol):
    def match(
        self, real: TrackedDetection, mirror: TrackedDetection
    ) -> tuple[TrackedDetection, TrackedDetection] | None: ...


class Reconstructor(Protocol):
    def reconstruct(self, real: TrackedDetection, mirror: TrackedDetection) -> TrajectoryPoint: ...


class BehaviorRecognizer(Protocol):
    def detect(
        self,
        trajectory: Sequence[TrajectoryPoint],
        speed: Sequence[float],
        angular_speed: Sequence[float],
    ) -> Sequence[BehaviorEvent]: ...

