"""Headless figures for synthetic 3D trajectories and motion curves."""

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fish3d.motion import MotionSample
from fish3d.schemas import TrajectoryPoint


def plot_trajectory(path: Path, points: Sequence[TrajectoryPoint]) -> None:
    """Save a 3D path, breaking the line at invalid observations."""

    figure = plt.figure(figsize=(8, 6))
    axis = figure.add_subplot(111, projection="3d")
    axis.plot(
        [point.X for point in points],
        [point.Y for point in points],
        [point.Z for point in points],
        color="navy",
    )
    unit = points[0].coordinate_unit
    axis.set(xlabel=f"X ({unit})", ylabel=f"Y ({unit})", zlabel=f"Z ({unit})", title="Synthetic 3D trajectory")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def plot_motion_curves(output_dir: Path, samples: Sequence[MotionSample]) -> None:
    """Save separate speed and angular-speed curves against actual timestamps."""

    times = [sample.point.timestamp_s for sample in samples]
    for filename, values, ylabel, title in (
        (
            "speed.png",
            [sample.speed for sample in samples],
            f"Speed ({samples[0].point.coordinate_unit}/s)",
            "Synthetic 3D speed",
        ),
        (
            "angular_speed.png",
            [sample.angular_speed_rad_s for sample in samples],
            "Angular speed (rad/s)",
            "Synthetic turning rate",
        ),
    ):
        figure, axis = plt.subplots(figsize=(8, 4))
        axis.plot(times, values, color="teal")
        finite_values = [value for value in values if value == value]
        if finite_values:
            axis.set_ylim(0, max(finite_values) * 1.15 if max(finite_values) > 0 else 1)
        axis.set(xlabel="Time (s)", ylabel=ylabel, title=title)
        axis.grid(alpha=0.25)
        figure.tight_layout()
        figure.savefig(output_dir / filename, dpi=150)
        plt.close(figure)

