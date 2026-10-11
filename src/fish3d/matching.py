"""Single-fish correspondence in synchronized, aligned ideal image views."""

from dataclasses import dataclass
from math import isfinite, nan
from pathlib import Path

import yaml

from fish3d.interfaces import TrackedDetection


@dataclass(frozen=True, slots=True)
class MatchingConfig:
    max_y_disparity_px: float

    def __post_init__(self) -> None:
        if not isfinite(self.max_y_disparity_px) or self.max_y_disparity_px < 0:
            raise ValueError("max_y_disparity_px must be finite and nonnegative")


def load_matching_config(path: Path) -> MatchingConfig:
    """Read the engineering y-disparity gate; frame/time equality is mandatory."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MatchingConfig(**document["matching"])


class SingleFishDualViewMatcher:
    """Match one real and one mirror centroid without equating view-local IDs.

    The y gate assumes aligned ideal coordinates. It is an engineering check,
    not a calibrated epipolar constraint or a proof of physical fish identity.
    """

    def __init__(self, config: MatchingConfig) -> None:
        self.config = config
        self.last_status = "uninitialized"
        self.last_y_disparity_px = nan

    def match(
        self, real: TrackedDetection, mirror: TrackedDetection,
    ) -> tuple[TrackedDetection, TrackedDetection] | None:
        """Return synchronized valid candidates, otherwise None with a reason."""

        left, right = real.detection, mirror.detection
        if left.view != "real" or right.view != "mirror":
            raise ValueError("arguments must be ordered real, mirror")
        self.last_y_disparity_px = nan
        for point in (left, right):
            if point.frame_id < 0 or not isfinite(point.timestamp_s) or point.timestamp_s < 0:
                raise ValueError("frame_id and timestamp_s must be nonnegative and finite")
            if point.is_valid and (
                not all(isfinite(value) for value in (point.x_px, point.y_px)) or point.area_px <= 0
            ):
                raise ValueError("valid detection requires finite coordinates and positive area")
        if left.frame_id != right.frame_id:
            self.last_status = "frame_mismatch"
        elif left.timestamp_s != right.timestamp_s:
            self.last_status = "timestamp_mismatch"
        elif not (left.is_valid and right.is_valid):
            self.last_status = "invalid_detection"
        elif not (real.fish_id and mirror.fish_id):
            self.last_status = "missing_track_id"
        else:
            self.last_y_disparity_px = abs(left.y_px - right.y_px)
            if self.last_y_disparity_px > self.config.max_y_disparity_px:
                self.last_status = "y_disparity_exceeded"
            else:
                self.last_status = "matched"
                return real, mirror
        return None
