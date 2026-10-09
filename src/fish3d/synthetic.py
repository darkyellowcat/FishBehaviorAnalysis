"""Deterministic constructed trajectories for software checks only."""

from math import cos, sin

from fish3d.config import SyntheticConfig
from fish3d.schemas import TrajectoryPoint


def generate_synthetic_trajectory(config: SyntheticConfig) -> list[TrajectoryPoint]:
    """Generate a helix; values are synthetic and have no experimental scale."""

    result = []
    for frame_id in range(config.sample_count):
        timestamp_s = frame_id * config.sample_interval_s
        angle = config.angular_rate_rad_s * timestamp_s
        result.append(
            TrajectoryPoint(
                frame_id=frame_id,
                timestamp_s=timestamp_s,
                fish_id=config.fish_id,
                X=config.radius * cos(angle),
                Y=config.radius * sin(angle),
                Z=config.vertical_speed * timestamp_s,
                coordinate_unit=config.coordinate_unit,
                is_valid=True,
                coordinate_frame=config.coordinate_frame,
                data_source="synthetic",
            )
        )
    return result

