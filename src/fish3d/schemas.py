"""Shared data contracts for trajectories and future video stages."""

from dataclasses import dataclass
from math import isfinite, isnan
from typing import Literal, Sequence

View = Literal["real", "mirror"]


@dataclass(frozen=True, slots=True)
class TrajectoryPoint:
    """One 3D observation; invalid observations carry NaN in all coordinates."""

    frame_id: int
    timestamp_s: float
    fish_id: str
    X: float
    Y: float
    Z: float
    coordinate_unit: str
    is_valid: bool
    coordinate_frame: str
    data_source: Literal["synthetic", "experimental"]

    def __post_init__(self) -> None:
        if self.frame_id < 0 or not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("frame_id and timestamp_s must be nonnegative and finite")
        if not self.fish_id or not self.coordinate_unit or not self.coordinate_frame:
            raise ValueError("fish_id, coordinate_unit, and coordinate_frame are required")
        if self.data_source not in ("synthetic", "experimental"):
            raise ValueError("data_source must be synthetic or experimental")
        coordinates = (self.X, self.Y, self.Z)
        if self.is_valid and not all(isfinite(value) for value in coordinates):
            raise ValueError("valid points require three finite coordinates")
        if not self.is_valid and not all(isnan(value) for value in coordinates):
            raise ValueError("invalid points require NaN in all coordinates")


def validate_trajectory(points: Sequence[TrajectoryPoint]) -> None:
    """Check one fish's ordered trajectory before any metric is calculated."""

    if not points:
        raise ValueError("trajectory is empty")
    first = points[0]
    for previous, current in zip(points, points[1:]):
        if current.fish_id != first.fish_id:
            raise ValueError("one trajectory may contain only one fish_id")
        if current.coordinate_unit != first.coordinate_unit:
            raise ValueError("coordinate_unit must be consistent")
        if current.coordinate_frame != first.coordinate_frame:
            raise ValueError("coordinate_frame must be consistent")
        if current.data_source != first.data_source:
            raise ValueError("data_source must be consistent")
        if current.frame_id <= previous.frame_id:
            raise ValueError("frame_id must increase strictly")
        if current.timestamp_s <= previous.timestamp_s:
            raise ValueError("timestamp_s must increase strictly")

