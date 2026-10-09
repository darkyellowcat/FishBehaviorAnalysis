import csv
import math

import pytest

from fish3d.export import export_trajectory
from fish3d.motion import analyze_motion, total_path_length
from fish3d.schemas import TrajectoryPoint


def point(frame: int, time: float, xyz: tuple[float, float, float] | None, unit: str = "synthetic_unit") -> TrajectoryPoint:
    x, y, z = xyz if xyz is not None else (math.nan, math.nan, math.nan)
    return TrajectoryPoint(frame, time, "fish_1", x, y, z, unit, xyz is not None, "test_frame", "synthetic")


def test_stationary_trajectory() -> None:
    samples = analyze_motion([point(i, float(i), (0.0, 0.0, 0.0)) for i in range(5)])
    assert total_path_length(samples) == 0
    assert all(sample.step_displacement == 0 for sample in samples[1:])
    assert all(sample.speed == 0 for sample in samples[1:-1])
    assert all(math.isnan(sample.turning_angle_rad) for sample in samples)
    assert all(math.isnan(sample.direction_xyz[0]) for sample in samples)


def test_constant_speed_straight_line_in_3d() -> None:
    samples = analyze_motion([point(i, float(i), (2.0 * i, 3.0 * i, 6.0 * i)) for i in range(5)])
    assert total_path_length(samples) == pytest.approx(28.0)
    assert samples[2].step_displacement == pytest.approx(7.0)
    assert samples[2].step_vector_xyz == pytest.approx((2.0, 3.0, 6.0))
    assert samples[2].velocity_xyz == pytest.approx((2.0, 3.0, 6.0))
    assert samples[2].speed == pytest.approx(7.0)
    assert samples[2].direction_xyz == pytest.approx((2 / 7, 3 / 7, 6 / 7))
    assert samples[2].turning_angle_rad == pytest.approx(0.0, abs=1e-7)
    assert math.isnan(samples[0].speed) and math.isnan(samples[-1].speed)


def test_uniform_turning() -> None:
    points = [
        point(0, 0.0, (0.0, 0.0, 0.0)),
        point(1, 1.0, (1.0, 0.0, 0.0)),
        point(2, 2.0, (1.0, 1.0, 0.0)),
        point(3, 3.0, (0.0, 1.0, 0.0)),
    ]
    samples = analyze_motion(points)
    assert samples[1].turning_angle_rad == pytest.approx(math.pi / 2)
    assert samples[2].turning_angle_rad == pytest.approx(math.pi / 2)
    assert samples[1].angular_speed_rad_s == pytest.approx(math.pi / 4)
    assert samples[2].angular_speed_rad_s == pytest.approx(math.pi / 4)
    assert total_path_length(samples) == pytest.approx(3.0)


def test_nonuniform_timestamps_use_actual_elapsed_time() -> None:
    samples = analyze_motion([
        point(0, 0.0, (0.0, 0.0, 0.0)),
        point(1, 1.0, (1.0, 2.0, 2.0)),
        point(2, 3.0, (3.0, 6.0, 6.0)),
    ])
    assert samples[1].velocity_xyz == pytest.approx((1.0, 2.0, 2.0))
    assert samples[1].speed == pytest.approx(3.0)


def test_missing_coordinates_break_path_and_centered_metrics() -> None:
    samples = analyze_motion([
        point(0, 0.0, (0.0, 0.0, 0.0)),
        point(1, 1.0, (1.0, 0.0, 0.0)),
        point(2, 2.0, None),
        point(3, 3.0, (3.0, 0.0, 0.0)),
        point(4, 4.0, (4.0, 0.0, 0.0)),
    ])
    assert total_path_length(samples) == pytest.approx(2.0)
    assert math.isnan(samples[2].step_displacement)
    assert math.isnan(samples[3].step_displacement)
    assert all(math.isnan(sample.speed) for sample in samples)


def test_zero_length_incoming_vector_has_no_turn_angle() -> None:
    samples = analyze_motion([
        point(0, 0.0, (0.0, 0.0, 0.0)),
        point(1, 1.0, (0.0, 0.0, 0.0)),
        point(2, 2.0, (1.0, 0.0, 0.0)),
    ])
    assert samples[1].speed == pytest.approx(0.5)
    assert math.isnan(samples[1].turning_angle_rad)
    assert math.isnan(samples[1].angular_speed_rad_s)


def test_near_zero_displacement_is_excluded_from_turn() -> None:
    samples = analyze_motion([
        point(0, 0.0, (0.0, 0.0, 0.0)),
        point(1, 1.0, (1e-10, 0.0, 0.0)),
        point(2, 2.0, (1.0, 0.0, 0.0)),
    ], min_direction_displacement=1e-9)
    assert math.isnan(samples[1].turning_angle_rad)


def test_frame_gap_breaks_path() -> None:
    samples = analyze_motion([
        point(0, 0.0, (0.0, 0.0, 0.0)),
        point(2, 2.0, (2.0, 0.0, 0.0)),
        point(3, 3.0, (3.0, 0.0, 0.0)),
    ])
    assert total_path_length(samples) == pytest.approx(1.0)
    assert math.isnan(samples[1].speed)


@pytest.mark.parametrize("unit", ["px", "mm"])
def test_coordinate_units_are_preserved(unit: str) -> None:
    samples = analyze_motion([point(i, float(i), (float(i), 0.0, 0.0), unit) for i in range(3)])
    assert samples[1].speed == pytest.approx(1.0)
    assert samples[1].point.coordinate_unit == unit


def test_invalid_csv_coordinate_is_explicit_nan(tmp_path) -> None:
    path = tmp_path / "trajectory.csv"
    export_trajectory(path, [point(0, 0.0, None)])
    with path.open(newline="", encoding="utf-8") as stream:
        row = next(csv.DictReader(stream))
    assert row["X"] == "NaN"
    assert row["is_valid"] == "false"
    assert row["data_source"] == "synthetic"

