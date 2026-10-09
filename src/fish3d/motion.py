"""Three-dimensional motion features from one fish's ordered trajectory."""

from dataclasses import dataclass
from math import acos
from typing import Sequence

import numpy as np

from fish3d.schemas import TrajectoryPoint, validate_trajectory

NAN3 = (float("nan"),) * 3


@dataclass(frozen=True, slots=True)
class MotionSample:
    """Features at a trajectory point; undefined values are NaN."""

    point: TrajectoryPoint
    step_vector_xyz: tuple[float, float, float]
    step_displacement: float
    cumulative_path_length: float
    velocity_xyz: tuple[float, float, float]
    speed: float
    direction_xyz: tuple[float, float, float]
    turning_angle_rad: float
    angular_speed_rad_s: float


def _coordinates(point: TrajectoryPoint) -> np.ndarray:
    return np.array((point.X, point.Y, point.Z), dtype=float)


def _adjacent(left: TrajectoryPoint, right: TrajectoryPoint) -> bool:
    return left.is_valid and right.is_valid and right.frame_id == left.frame_id + 1


def analyze_motion(
    points: Sequence[TrajectoryPoint], *, min_direction_displacement: float = 0.0
) -> list[MotionSample]:
    """Calculate step path and centered velocity/turning features.

    A missing frame or invalid point breaks adjacent segments. Endpoints have no
    centered features. Turning angle uses incoming/outgoing 3D displacements,
    divided by the outer timestamps as specified by the project task book.
    """

    validate_trajectory(points)
    if min_direction_displacement < 0:
        raise ValueError("min_direction_displacement must be nonnegative")

    results = []
    cumulative = 0.0
    for index, current in enumerate(points):
        step_vector = NAN3
        step = float("nan")
        if index > 0 and _adjacent(points[index - 1], current):
            displacement = _coordinates(current) - _coordinates(points[index - 1])
            step_vector = tuple(float(value) for value in displacement)
            step = float(np.linalg.norm(displacement))
            cumulative += step

        velocity = NAN3
        speed = float("nan")
        direction = NAN3
        turn = float("nan")
        angular_speed = float("nan")
        if 0 < index < len(points) - 1:
            previous, following = points[index - 1], points[index + 1]
            if _adjacent(previous, current) and _adjacent(current, following):
                first = _coordinates(current) - _coordinates(previous)
                second = _coordinates(following) - _coordinates(current)
                outer_dt = following.timestamp_s - previous.timestamp_s
                delta = first + second
                velocity_vector = delta / outer_dt
                velocity = tuple(float(value) for value in velocity_vector)
                speed = float(np.linalg.norm(velocity_vector))
                delta_length = float(np.linalg.norm(delta))
                if delta_length > min_direction_displacement:
                    direction = tuple(float(value) for value in delta / delta_length)

                first_length = float(np.linalg.norm(first))
                second_length = float(np.linalg.norm(second))
                if first_length > min_direction_displacement and second_length > min_direction_displacement:
                    cosine = float(np.dot(first, second) / (first_length * second_length))
                    turn = acos(max(-1.0, min(1.0, cosine)))
                    angular_speed = turn / outer_dt

        results.append(
            MotionSample(current, step_vector, step, cumulative, velocity, speed, direction, turn, angular_speed)
        )
    return results


def total_path_length(samples: Sequence[MotionSample]) -> float:
    """Return the sum of valid adjacent 3D steps."""

    return samples[-1].cumulative_path_length if samples else 0.0

