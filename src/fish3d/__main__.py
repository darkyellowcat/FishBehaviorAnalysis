"""Command-line entry points for synthetic trajectory and S2 video work."""

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
    video_demo = subparsers.add_parser("video-demo", help="generate and preprocess an S2 synthetic video")
    video_demo.add_argument("--config", type=Path, required=True)
    video_demo.add_argument("--output", type=Path, required=True)
    process = subparsers.add_parser("preprocess-video", help="preprocess an existing video")
    process.add_argument("--input", type=Path, required=True)
    process.add_argument("--config", type=Path, required=True)
    process.add_argument("--output", type=Path, required=True)
    som_demo = subparsers.add_parser("som-demo", help="generate and segment a synthetic S3 video")
    som_demo.add_argument("--config", type=Path, required=True)
    som_demo.add_argument("--output", type=Path, required=True)
    segment = subparsers.add_parser("segment-video", help="run LBAdaptiveSOM on an existing video")
    segment.add_argument("--input", type=Path, required=True)
    segment.add_argument("--config", type=Path, required=True)
    segment.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command in ("som-demo", "segment-video"):
        from fish3d.foreground_processing import segment_video
        from fish3d.video_config import load_video_config
        from fish3d.video_io import generate_synthetic_video

        if args.command == "som-demo":
            video_path = args.output / "synthetic_input.avi"
            generate_synthetic_video(video_path, load_video_config(args.config))
        else:
            video_path = args.input
        manifest = segment_video(video_path, args.config, args.output)
        print(f"Segmented {manifest['frame_count']} {manifest['data_source']} frames with LBAdaptiveSOM in {args.output.resolve()}")
        return

    if args.command in ("video-demo", "preprocess-video"):
        from fish3d.video_config import load_video_config
        from fish3d.video_io import generate_synthetic_video
        from fish3d.video_processing import preprocess_video

        if args.command == "video-demo":
            config = load_video_config(args.config)
            video_path = args.output / "synthetic_input.avi"
            generate_synthetic_video(video_path, config)
        else:
            video_path = args.input
        manifest = preprocess_video(video_path, args.config, args.output)
        print(f"Processed {manifest['frame_count']} {manifest['data_source']} video frames in {args.output.resolve()}")
        return

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

