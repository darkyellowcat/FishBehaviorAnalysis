"""S6 CSV workflow: observed motion, paper rules, plots, and provenance."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from math import isfinite
from pathlib import Path
from typing import Sequence

import matplotlib
import numpy as np
import yaml

from fish3d import __version__
from fish3d.behavior import BEHAVIORS, BEHAVIOR_VERSION, RuleBehaviorRecognizer, continuous, load_behavior_config
from fish3d.export import export_motion
from fish3d.motion import MotionSample, analyze_motion
from fish3d.schemas import TrajectoryPoint


def read_trajectory(path: Path) -> list[TrajectoryPoint]:
    """Read S1/S5 observations, retaining NaN and rejecting reordered input.

    S5 supplies one point per frame, with potentially changing segment IDs.
    This entry point does not accept simultaneous multiple fish in one frame.
    """

    points = []
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            valid = row["is_valid"].lower()
            if valid not in ("true", "false"):
                raise ValueError("is_valid must be true or false")
            point = TrajectoryPoint(
                int(row["frame_id"]), float(row["timestamp_s"]), row["fish_id"],
                *(float(row[key]) for key in ("X", "Y", "Z")),
                row["coordinate_unit"], valid == "true", row["coordinate_frame"], row["data_source"],
            )
            if points and (point.frame_id <= points[-1].frame_id or point.timestamp_s <= points[-1].timestamp_s):
                raise ValueError("frame IDs and timestamps must increase strictly")
            points.append(point)
    if not points:
        raise ValueError("trajectory is empty")
    return points


def continuity_runs(points: Sequence[TrajectoryPoint], max_gap_s: float) -> list[list[TrajectoryPoint]]:
    """Split before motion differentiation, so long time gaps cannot bridge."""

    runs = []
    for point in points:
        if not runs or not continuous(runs[-1][-1], point, max_gap_s):
            runs.append([])
        runs[-1].append(point)
    return runs


def observed_motion(points: Sequence[TrajectoryPoint], *, max_gap_s: float,
                    min_direction_displacement: float) -> list[MotionSample]:
    """Reuse S1 on continuity runs; accumulate only observed path per fish ID."""

    samples = []
    totals = defaultdict(float)
    for run in continuity_runs(points, max_gap_s):
        identity = run[0].fish_id
        result = analyze_motion(run, min_direction_displacement=min_direction_displacement)
        samples.extend(replace(sample, cumulative_path_length=totals[identity] + sample.cumulative_path_length)
                       for sample in result)
        totals[identity] += result[-1].cumulative_path_length
    return samples


def generate_behavior_demo(config_path: Path) -> list[TrajectoryPoint]:
    """Construct configured piecewise linear observations, never behavior flags."""

    config = load_behavior_config(config_path)
    if config.data_source != "synthetic":
        raise ValueError("behavior-demo requires data_source=synthetic")
    fixture = yaml.safe_load(config_path.read_text(encoding="utf-8"))["synthetic_behavior"]
    interval = fixture["sample_interval_s"]
    if not isfinite(interval) or interval <= 0 or not fixture["fish_id"] or not fixture["phases"]:
        raise ValueError("synthetic fixture requires positive interval, fish_id, and phases")
    points = []
    for phase in fixture["phases"]:
        count, start, velocity = phase["sample_count"], phase["start_xyz"], phase["velocity_xyz"]
        if (not isinstance(count, int) or count < 1 or len(start) != 3 or len(velocity) != 3
                or not all(isfinite(value) for value in (*start, *velocity))):
            raise ValueError("synthetic phase requires positive count and finite XYZ/velocity vectors")
        for index in range(count):
            frame = len(points)
            coordinates = tuple(start[axis] + velocity[axis] * index * interval for axis in range(3))
            points.append(TrajectoryPoint(frame, frame * interval, fixture["fish_id"], *coordinates,
                                          config.coordinate_unit, True, config.coordinate_frame, "synthetic"))
    return points


def analyze_behavior(input_path: Path, config_path: Path, output_dir: Path) -> dict:
    """Analyze S1/S5 CSV without inferring unknown positions or real accuracy."""

    from fish3d.behavior_visualization import plot_behavior

    config = load_behavior_config(config_path)
    points = read_trajectory(input_path)
    if any((point.coordinate_unit, point.coordinate_frame, point.data_source) != (
        config.coordinate_unit, config.coordinate_frame, config.data_source,
    ) for point in points):
        raise ValueError("trajectory unit/frame/data_source must match behavior configuration")
    motion = observed_motion(points, max_gap_s=config.max_gap_s,
                             min_direction_displacement=config.min_direction_displacement)
    groups = defaultdict(list)
    for sample in motion:
        groups[sample.point.fish_id].append(sample)
    recognizer = RuleBehaviorRecognizer(config)
    samples, events = [], []
    for group in groups.values():
        flags, found = recognizer.evaluate([sample.point for sample in group],
                                          [sample.speed for sample in group],
                                          [sample.angular_speed_rad_s for sample in group])
        samples.extend(flags)
        events.extend(found)
    samples.sort(key=lambda sample: sample.point.frame_id)
    events.sort(key=lambda event: (event.start_s, event.fish_id, event.behavior))
    output_dir.mkdir(parents=True, exist_ok=True)
    export_motion(output_dir / "motion.csv", motion)
    sample_columns = ("frame_id", "timestamp_s", "fish_id", "is_valid", "frantic_evaluable",
                      *BEHAVIORS, "surface_duration_s", "coordinate_unit", "coordinate_frame", "data_source")
    with (output_dir / "behavior_samples.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sample_columns)
        writer.writeheader()
        for sample in samples:
            point = sample.point
            row = {key: getattr(point, key) for key in (
                "frame_id", "timestamp_s", "fish_id", "is_valid", "coordinate_unit", "coordinate_frame", "data_source")}
            row.update({key: getattr(sample, key) for key in (*BEHAVIORS, "surface_duration_s", "frantic_evaluable")})
            row = {key: str(value).lower() if isinstance(value, bool) else value for key, value in row.items()}
            writer.writerow(row)
    event_columns = ("fish_id", "behavior", "start_s", "end_s", "observed_duration_s", "data_source",
                     "coordinate_unit", "coordinate_frame", "result_type")
    with (output_dir / "behavior_events.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=event_columns)
        writer.writeheader()
        for event in events:
            writer.writerow({**asdict(event), "observed_duration_s": event.end_s - event.start_s,
                             "data_source": config.data_source, "coordinate_unit": config.coordinate_unit,
                             "coordinate_frame": config.coordinate_frame, "result_type": "rule_prediction"})
    plot_behavior(output_dir, points, motion, samples, config)
    manifest = {
        "stage": "S6", "behavior_algorithm_version": BEHAVIOR_VERSION, "package_version": __version__,
        "numpy_version": np.__version__, "matplotlib_version": matplotlib.__version__,
        "data_source": config.data_source, "coordinate_unit": config.coordinate_unit,
        "coordinate_frame": config.coordinate_frame, "speed_unit": f"{config.coordinate_unit}/s",
        "angular_speed_unit": "rad/s", "frame_count": len(points),
        "valid_point_count": sum(point.is_valid for point in points), "fish_id_count": len(groups),
        "event_counts": dict(Counter(event.behavior for event in events)),
        "input_trajectory": str(input_path.resolve()),
        "input_trajectory_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "config_file": str(config_path.resolve()), "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "config_snapshot": yaml.safe_load(config_path.read_text(encoding="utf-8")),
        "behavior_accuracy_validated_on_real_data": False,
        "output_files": ["motion.csv", "behavior_samples.csv", "behavior_events.csv", "trajectory_3d.png",
                         "motion_behavior.png", "behavior_timeline.png", "run_manifest.json"],
        "limitations": [
            "Rule predictions only; no real-video behavior accuracy or validated threshold transfer.",
            "Z must increase upward; water height and tolerances require independent calibration in the same frame/unit.",
            "No position interpolation, endpoint differentiation, smoothing, or missing-data normality claim.",
            "Float events start at the first sample exceeding the duration threshold, not at first surface contact.",
            "Event ends are last true observations; single-sample events have zero observed duration.",
            "Paper height/duration predicate does not prove immobility; rules may overlap.",
            "S5 model_px remains an unverified ideal model, not a physical height or physical speed.",
        ],
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    return manifest
