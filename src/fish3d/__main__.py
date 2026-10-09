"""Command-line entry point for S1 synthetic analysis."""

import argparse
from pathlib import Path

from fish3d.config import load_config
from fish3d.export import export_manifest, export_motion, export_trajectory
from fish3d.motion import analyze_motion
from fish3d.synthetic import generate_synthetic_trajectory
from fish3d.visualization import plot_motion_curves, plot_trajectory


def main() -> None:
    parser = argparse.ArgumentParser(description="Fish 3D trajectory tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    simulate = subparsers.add_parser("simulate", help="generate synthetic S1 outputs")
    simulate.add_argument("--config", type=Path, required=True)
    simulate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    points = generate_synthetic_trajectory(config)
    motion = analyze_motion(points, min_direction_displacement=config.min_direction_displacement)
    args.output.mkdir(parents=True, exist_ok=True)
    export_trajectory(args.output / "trajectory_3d.csv", points)
    export_motion(args.output / "motion.csv", motion)
    plot_trajectory(args.output / "trajectory_3d.png", points)
    plot_motion_curves(args.output, motion)
    filenames = ("trajectory_3d.csv", "motion.csv", "trajectory_3d.png", "speed.png", "angular_speed.png", "run_manifest.json")
    export_manifest(args.output / "run_manifest.json", args.config, config, filenames)
    print(f"Generated synthetic outputs in {args.output.resolve()}")


if __name__ == "__main__":
    main()

