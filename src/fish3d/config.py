"""Validated configuration for the S0/S1 synthetic workflow."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class SyntheticConfig:
    fish_id: str
    sample_count: int
    sample_interval_s: float
    radius: float
    angular_rate_rad_s: float
    vertical_speed: float
    min_direction_displacement: float
    coordinate_unit: str
    coordinate_frame: str

    def __post_init__(self) -> None:
        if not self.fish_id or not self.coordinate_unit or not self.coordinate_frame:
            raise ValueError("fish_id, coordinate_unit, and coordinate_frame are required")
        if self.sample_count < 3:
            raise ValueError("sample_count must be at least 3")
        if self.sample_interval_s <= 0 or self.radius <= 0 or self.angular_rate_rad_s <= 0:
            raise ValueError("sampling interval, radius, and angular rate must be positive")
        if self.min_direction_displacement < 0:
            raise ValueError("min_direction_displacement must be nonnegative")


def load_config(path: Path) -> SyntheticConfig:
    """Read the versioned YAML example configuration."""

    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("synthetic"), dict):
        raise ValueError("configuration requires a synthetic mapping")
    return SyntheticConfig(**document["synthetic"])

