"""CSV and provenance output for the synthetic demonstration."""

import csv
import hashlib
import json
from dataclasses import asdict
from math import isnan
from pathlib import Path
from typing import Sequence

from fish3d import __version__
from fish3d.config import SyntheticConfig
from fish3d.motion import MotionSample
from fish3d.schemas import TrajectoryPoint


def _value(number: float) -> float | str:
    return "NaN" if isnan(number) else number


def export_trajectory(path: Path, points: Sequence[TrajectoryPoint]) -> None:
    """Write one row per input frame, retaining invalid observations."""

    columns = (
        "frame_id", "timestamp_s", "fish_id", "X", "Y", "Z",
        "coordinate_unit", "is_valid", "coordinate_frame", "data_source",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for point in points:
            row = asdict(point)
            row.update({key: _value(row[key]) for key in ("X", "Y", "Z")})
            row["is_valid"] = str(point.is_valid).lower()
            writer.writerow(row)


def export_motion(path: Path, samples: Sequence[MotionSample]) -> None:
    """Write path, 3D velocity, direction, and turn metrics with units."""

    columns = (
        "frame_id", "timestamp_s", "fish_id", "step_dx", "step_dy", "step_dz", "step_displacement",
        "cumulative_path_length", "velocity_x", "velocity_y", "velocity_z",
        "speed", "direction_x", "direction_y", "direction_z",
        "turning_angle_rad", "angular_speed_rad_s", "coordinate_unit",
        "coordinate_frame", "is_valid", "speed_unit", "data_source",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for sample in samples:
            point = sample.point
            row = {
                "frame_id": point.frame_id,
                "timestamp_s": point.timestamp_s,
                "fish_id": point.fish_id,
                "step_dx": _value(sample.step_vector_xyz[0]),
                "step_dy": _value(sample.step_vector_xyz[1]),
                "step_dz": _value(sample.step_vector_xyz[2]),
                "step_displacement": _value(sample.step_displacement),
                "cumulative_path_length": sample.cumulative_path_length,
                "velocity_x": _value(sample.velocity_xyz[0]),
                "velocity_y": _value(sample.velocity_xyz[1]),
                "velocity_z": _value(sample.velocity_xyz[2]),
                "speed": _value(sample.speed),
                "direction_x": _value(sample.direction_xyz[0]),
                "direction_y": _value(sample.direction_xyz[1]),
                "direction_z": _value(sample.direction_xyz[2]),
                "turning_angle_rad": _value(sample.turning_angle_rad),
                "angular_speed_rad_s": _value(sample.angular_speed_rad_s),
                "coordinate_unit": point.coordinate_unit,
                "coordinate_frame": point.coordinate_frame,
                "is_valid": str(point.is_valid).lower(),
                "speed_unit": f"{point.coordinate_unit}/s",
                "data_source": point.data_source,
            }
            writer.writerow(row)


def export_manifest(path: Path, config_path: Path, config: SyntheticConfig, output_files: Sequence[str]) -> None:
    """Record the exact synthetic configuration and source file hash."""

    document = {
        "data_source": "synthetic",
        "algorithm_version": __version__,
        "config_path": str(config_path.resolve()),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "config": {"synthetic": asdict(config)},
        "output_files": list(output_files),
        "limitations": "Constructed trajectory only; no physical calibration or real-video validation.",
    }
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

