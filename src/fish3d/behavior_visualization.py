"""S6 figures show observed segments, thresholds, and independent rule flags."""

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fish3d.behavior import BEHAVIORS, BehaviorConfig, BehaviorSample
from fish3d.motion import MotionSample
from fish3d.schemas import TrajectoryPoint


def plot_behavior(output_dir: Path, points: Sequence[TrajectoryPoint], motion: Sequence[MotionSample],
                  samples: Sequence[BehaviorSample], config: BehaviorConfig) -> None:
    """Draw source-labelled 3D paths, feature/height curves, and rule samples."""

    from fish3d.behavior_processing import continuity_runs

    title = f"{config.data_source.upper()} - rule predictions, unvalidated on real data"
    runs = continuity_runs(points, config.max_gap_s)
    identities = list(dict.fromkeys(point.fish_id for point in points))
    colors = {identity: plt.get_cmap("tab10")(index % 10) for index, identity in enumerate(identities)}
    figure = plt.figure(figsize=(8, 6))
    axis = figure.add_subplot(111, projection="3d")
    labelled = set()
    for run in runs:
        valid = [point for point in run if point.is_valid]
        if not valid:
            continue
        identity = valid[0].fish_id
        axis.plot([point.X for point in valid], [point.Y for point in valid], [point.Z for point in valid],
                  ".-", color=colors[identity], label=identity if identity not in labelled else None)
        labelled.add(identity)
    for label, setter in (("X", axis.set_xlabel), ("Y", axis.set_ylabel), ("Z", axis.set_zlabel)):
        setter(f"{label} ({config.coordinate_unit})")
    axis.set_title(title, fontsize=10)
    if labelled:
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output_dir / "trajectory_3d.png", dpi=150)
    plt.close(figure)

    by_frame = {sample.point.frame_id: sample for sample in motion}
    figure, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    for run in runs:
        times = [point.timestamp_s for point in run]
        color = colors[run[0].fish_id]
        axes[0].plot(times, [by_frame[point.frame_id].speed for point in run], ".-", color=color)
        axes[1].plot(times, [by_frame[point.frame_id].angular_speed_rad_s for point in run], ".-", color=color)
        axes[2].plot(times, [point.Z for point in run], ".-", color=color)
    axes[0].axhline(config.frantic_speed, color="red", linestyle="--", label="frantic threshold")
    axes[1].axhline(config.frantic_angular_speed_rad_s, color="red", linestyle="--", label="frantic threshold")
    axes[2].axhline(config.water_surface_z, color="blue", linestyle="--", label="water surface")
    axes[2].axhspan(config.water_surface_z - config.surface_tolerance,
                   config.water_surface_z + config.surface_tolerance, color="blue", alpha=0.12)
    axes[0].set_ylabel(f"Speed ({config.coordinate_unit}/s)")
    axes[1].set_ylabel("Angular speed (rad/s)")
    axes[2].set_ylabel(f"Z ({config.coordinate_unit})")
    axes[2].set_xlabel("Time (s)")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    figure.suptitle(title, fontsize=11)
    figure.tight_layout()
    figure.savefig(output_dir / "motion_behavior.png", dpi=150)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 3.5))
    for index, behavior in enumerate(BEHAVIORS):
        selected = [sample for sample in samples if getattr(sample, behavior)]
        axis.scatter([sample.point.timestamp_s for sample in selected], [index] * len(selected),
                     color=f"C{index}", marker="|", s=100, label=behavior)
    invalid = [sample.point.timestamp_s for sample in samples if not sample.point.is_valid]
    unknown = [sample.point.timestamp_s for sample in samples
               if sample.point.is_valid and not sample.frantic_evaluable]
    axis.scatter(invalid, [-1] * len(invalid), color="black", marker="x", label="invalid coordinate")
    axis.scatter(unknown, [-2] * len(unknown), color="gray", marker="x", label="frantic unknown")
    axis.set_yticks([-2, -1, *range(len(BEHAVIORS))], ["frantic unknown", "invalid coordinate", *BEHAVIORS])
    axis.set_xlim(points[0].timestamp_s - 0.5, points[-1].timestamp_s + 0.5)
    axis.set_xlabel("Time (s); marks indicate observations only")
    axis.set_title(title, fontsize=10)
    axis.grid(axis="x", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_dir / "behavior_timeline.png", dpi=150)
    plt.close(figure)
