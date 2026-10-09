import math
from pathlib import Path

import pytest

from fish3d.config import load_config
from fish3d.schemas import TrajectoryPoint, validate_trajectory


def point(frame: int, time: float, *, unit: str = "synthetic_unit", valid: bool = True) -> TrajectoryPoint:
    value = 1.0 if valid else math.nan
    return TrajectoryPoint(
        frame, time, "fish_1", value, value, value, unit, valid,
        "synthetic_cartesian", "synthetic",
    )


def test_default_config_loads() -> None:
    config = load_config(Path("configs/default.yaml"))
    assert config.sample_count >= 3
    assert config.coordinate_unit == "synthetic_unit"


def test_invalid_point_requires_nan() -> None:
    with pytest.raises(ValueError, match="NaN"):
        TrajectoryPoint(0, 0.0, "fish_1", 0.0, 0.0, 0.0, "px", False, "image", "synthetic")
    assert not point(0, 0.0, valid=False).is_valid


def test_repeated_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timestamp_s"):
        validate_trajectory([point(0, 0.0), point(1, 0.0)])


def test_unit_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="coordinate_unit"):
        validate_trajectory([point(0, 0.0), point(1, 1.0, unit="mm")])

