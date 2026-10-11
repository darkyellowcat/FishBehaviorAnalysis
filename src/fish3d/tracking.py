"""Timestamp-aware single-fish association; no predicted observations."""

from dataclasses import dataclass
from math import hypot, isfinite, isnan, nan
from pathlib import Path
from typing import Sequence

import yaml

from fish3d.interfaces import Detection2D, TrackedDetection
from fish3d.schemas import View


@dataclass(frozen=True, slots=True)
class TrackingConfig:
    max_speed_px_s: float
    max_gap_s: float

    def __post_init__(self) -> None:
        if not isfinite(self.max_speed_px_s) or self.max_speed_px_s <= 0:
            raise ValueError("max_speed_px_s must be finite and positive")
        if not isfinite(self.max_gap_s) or self.max_gap_s <= 0:
            raise ValueError("max_gap_s must be finite and positive")


def load_tracking_config(path: Path) -> TrackingConfig:
    """Read engineering association limits, in image pixels and seconds."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TrackingConfig(**document["tracking"])


def missing_detection(frame_id: int, timestamp_s: float, view: View) -> Detection2D:
    """Represent a missing observation without inventing a position."""

    return Detection2D(frame_id, timestamp_s, view, nan, nan, 0, False)


class SingleFishTracker:
    """Keep one view-local track while elapsed-time and displacement gates pass.

    IDs denote continuous 2D track segments, not confirmed physical fish identity.
    A long gap starts a new segment. Short gaps retain an ID but remain invalid.
    """

    def __init__(self, view: View, config: TrackingConfig) -> None:
        if view not in ("mirror", "real"):
            raise ValueError("view must be mirror or real")
        self.view = view
        self.config = config
        self._last_accepted: Detection2D | None = None
        self._previous: Detection2D | None = None
        self._segment_count = 0
        self._fish_id = ""
        self.last_status = "uninitialized"

    def update(self, detection: Detection2D) -> TrackedDetection:
        """Process every frame, including explicit invalid/missing detections."""

        if detection.view != self.view:
            raise ValueError("detection view does not match tracker")
        if detection.frame_id < 0 or not isfinite(detection.timestamp_s) or detection.timestamp_s < 0:
            raise ValueError("frame_id and timestamp_s must be nonnegative and finite")
        if detection.is_valid:
            if not all(isfinite(v) for v in (detection.x_px, detection.y_px)) or detection.area_px <= 0:
                raise ValueError("valid detection requires finite coordinates and positive area")
        elif not (isnan(detection.x_px) and isnan(detection.y_px) and detection.area_px == 0):
            raise ValueError("invalid detection requires NaN coordinates and zero area")
        if self._previous is not None:
            if detection.frame_id <= self._previous.frame_id or detection.timestamp_s <= self._previous.timestamp_s:
                raise ValueError("frame_id and timestamp_s must increase strictly")
        self._previous = detection
        last = self._last_accepted
        if last is not None and detection.timestamp_s - last.timestamp_s > self.config.max_gap_s:
            self._last_accepted = last = None
            self._fish_id = ""
        if not detection.is_valid:
            self.last_status = "missing" if last is not None else "uninitialized"
            return TrackedDetection(detection, self._fish_id)
        if last is not None:
            elapsed = detection.timestamp_s - last.timestamp_s
            displacement = hypot(detection.x_px - last.x_px, detection.y_px - last.y_px)
            if displacement > self.config.max_speed_px_s * elapsed:
                self.last_status = "rejected"
                return TrackedDetection(
                    missing_detection(detection.frame_id, detection.timestamp_s, self.view),
                    self._fish_id,
                )
        else:
            self._segment_count += 1
            self._fish_id = f"{self.view}_{self._segment_count:04d}"
        self.last_status = "initialized" if last is None else "tracked"
        self._last_accepted = detection
        return TrackedDetection(detection, self._fish_id)

    def track(self, detections: Sequence[Detection2D]) -> tuple[TrackedDetection, ...]:
        """Process an ordered sequence, continuing this instance's current state."""

        return tuple(self.update(detection) for detection in detections)
