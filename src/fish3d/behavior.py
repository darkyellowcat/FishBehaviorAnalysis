"""Paper table-1 predicates, with explicit sampling continuity and units."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Sequence

import yaml

from fish3d.interfaces import BehaviorEvent
from fish3d.schemas import TrajectoryPoint, validate_trajectory

BEHAVIOR_VERSION = "paper-table1-s6-v1"
BEHAVIORS = ("frantic_swimming", "float_surface", "jump_out")


@dataclass(frozen=True, slots=True)
class BehaviorConfig:
    """Threshold heights/displacements use coordinate_unit; angles use rad/s."""

    data_source: str
    coordinate_unit: str
    coordinate_frame: str
    water_surface_z: float
    surface_tolerance: float
    floating_duration_s: float
    frantic_speed: float
    frantic_angular_speed_rad_s: float
    max_gap_s: float
    min_direction_displacement: float

    def __post_init__(self) -> None:
        if self.data_source not in ("synthetic", "experimental"):
            raise ValueError("data_source must be synthetic or experimental")
        if not self.coordinate_unit or not self.coordinate_frame:
            raise ValueError("coordinate unit and frame are required")
        if not isfinite(self.water_surface_z):
            raise ValueError("water_surface_z must be finite")
        for name in ("surface_tolerance", "floating_duration_s", "frantic_speed",
                     "frantic_angular_speed_rad_s", "min_direction_displacement"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if not isfinite(self.max_gap_s) or self.max_gap_s <= 0:
            raise ValueError("max_gap_s must be finite and positive")


def load_behavior_config(path: Path) -> BehaviorConfig:
    """Read a behavior mapping without changing other stage configurations."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("behavior"), dict):
        raise ValueError("configuration requires a behavior mapping")
    return BehaviorConfig(**document["behavior"])


def continuous(left: TrajectoryPoint, right: TrajectoryPoint, max_gap_s: float) -> bool:
    """Two observed points form a segment only within one continuous identity."""

    return (left.is_valid and right.is_valid and left.fish_id == right.fish_id
            and right.frame_id == left.frame_id + 1
            and 0 < right.timestamp_s - left.timestamp_s <= max_gap_s)


@dataclass(frozen=True, slots=True)
class BehaviorSample:
    """False flags on invalid points are non-detections, not normality labels."""

    point: TrajectoryPoint
    frantic_swimming: bool
    float_surface: bool
    jump_out: bool
    surface_duration_s: float
    frantic_evaluable: bool


class RuleBehaviorRecognizer:
    """Keep paper predicates independent; detect() satisfies BehaviorRecognizer."""

    def __init__(self, config: BehaviorConfig):
        self.config = config

    def evaluate(
        self, trajectory: Sequence[TrajectoryPoint], speed: Sequence[float],
        angular_speed: Sequence[float],
    ) -> tuple[list[BehaviorSample], list[BehaviorEvent]]:
        """Return sample flags and contiguous intervals where each rule is true.

        Floating is true only after the strict duration threshold is exceeded.
        Unknown speed/angle (NaN) cannot trigger their respective predicates.
        If one finite metric exceeds its threshold, the OR rule is evaluable;
        otherwise both metrics must be finite to call a negative evaluable.
        """

        validate_trajectory(trajectory)
        if len(speed) != len(trajectory) or len(angular_speed) != len(trajectory):
            raise ValueError("feature lengths must match trajectory")
        cfg = self.config
        for point in trajectory:
            if (point.coordinate_unit, point.coordinate_frame, point.data_source) != (
                cfg.coordinate_unit, cfg.coordinate_frame, cfg.data_source,
            ):
                raise ValueError("trajectory unit/frame/data_source must match behavior configuration")
        samples = []
        surface_start = None
        for index, (point, velocity, angular) in enumerate(zip(trajectory, speed, angular_speed)):
            if index == 0 or not continuous(trajectory[index - 1], point, cfg.max_gap_s):
                surface_start = None
            at_surface = point.is_valid and abs(point.Z - cfg.water_surface_z) <= cfg.surface_tolerance
            if at_surface:
                if surface_start is None:
                    surface_start = point.timestamp_s
                duration = point.timestamp_s - surface_start
            else:
                surface_start = None
                duration = 0.0 if point.is_valid else float("nan")
            fast = point.is_valid and (
                (isfinite(velocity) and velocity > cfg.frantic_speed)
                or (isfinite(angular) and angular > cfg.frantic_angular_speed_rad_s)
            )
            samples.append(BehaviorSample(
                point, fast, at_surface and duration > cfg.floating_duration_s,
                point.is_valid and point.Z > cfg.water_surface_z, duration,
                point.is_valid and (fast or (isfinite(velocity) and isfinite(angular))),
            ))
        events = []
        for behavior in BEHAVIORS:
            start = end = None
            for index, sample in enumerate(samples):
                connected = index > 0 and continuous(samples[index - 1].point, sample.point, cfg.max_gap_s)
                if start is not None and (not connected or not getattr(sample, behavior)):
                    events.append(BehaviorEvent(trajectory[0].fish_id, behavior, start, end))
                    start = end = None
                if getattr(sample, behavior):
                    if start is None:
                        start = sample.point.timestamp_s
                    end = sample.point.timestamp_s
            if start is not None:
                events.append(BehaviorEvent(trajectory[0].fish_id, behavior, start, end))
        return samples, sorted(events, key=lambda event: (event.start_s, event.behavior))

    def detect(
        self, trajectory: Sequence[TrajectoryPoint], speed: Sequence[float],
        angular_speed: Sequence[float],
    ) -> list[BehaviorEvent]:
        """Return rule events; features must follow the supplied trajectory order."""

        return self.evaluate(trajectory, speed, angular_speed)[1]
