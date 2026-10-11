import csv
import hashlib
from dataclasses import asdict, replace
from math import isnan, pi
from pathlib import Path

import pytest
import yaml

from fish3d.behavior import RuleBehaviorRecognizer, load_behavior_config
from fish3d.behavior_processing import analyze_behavior, generate_behavior_demo, observed_motion, read_trajectory
from fish3d.export import export_trajectory
from fish3d.schemas import TrajectoryPoint


def configuration(**changes):
    return replace(load_behavior_config(Path("configs/synthetic_behavior.yaml")), **changes)


def point(frame, time=None, *, xyz=(0, 0, 10), identity="fish", valid=True):
    return TrajectoryPoint(frame, frame if time is None else time, identity,
                           *(xyz if valid else (float("nan"),) * 3),
                           "synthetic_unit", valid, "synthetic_cartesian", "synthetic")


def evaluate(points, config=None, speeds=None, angles=None):
    return RuleBehaviorRecognizer(config or configuration()).evaluate(
        points, [0.0] * len(points) if speeds is None else speeds,
        [0.0] * len(points) if angles is None else angles,
    )


def test_stationary_surface_strict_duration_and_event_confirmation_start() -> None:
    points = [point(frame) for frame in range(20)]
    motion = observed_motion(points, max_gap_s=1.5, min_direction_displacement=0.001)
    samples, events = evaluate(points, speeds=[sample.speed for sample in motion],
                               angles=[sample.angular_speed_rad_s for sample in motion])
    assert not any(sample.frantic_swimming or sample.jump_out for sample in samples)
    assert samples[15].surface_duration_s == 15 and not samples[15].float_surface
    assert samples[16].float_surface
    assert [(event.behavior, event.start_s, event.end_s) for event in events] == [("float_surface", 16, 19)]
    assert motion[1].speed == 0 and isnan(motion[1].angular_speed_rad_s)
    assert not samples[1].frantic_evaluable  # no turning direction for a stationary point


def test_frantic_or_rule_strict_boundaries_and_nan_unknown() -> None:
    points = [point(frame, xyz=(frame, 0, 4)) for frame in range(7)]
    samples, _ = evaluate(points,
                         speeds=[5, 5.01, 0, float("nan"), float("nan"), 5, 0],
                         angles=[1.7, 0, 1.71, 2, float("nan"), float("nan"), float("nan")])
    assert [sample.frantic_swimming for sample in samples] == [False, True, True, True, False, False, False]
    assert [sample.frantic_evaluable for sample in samples] == [True, True, True, True, False, False, False]


def test_surface_tolerance_jump_boundary_and_independent_overlapping_rules() -> None:
    points = [point(index, xyz=(0, 0, z)) for index, z in enumerate([9.5, 10, 10.5, 10.51])]
    samples, _ = evaluate(points, configuration(surface_tolerance=0.5, floating_duration_s=0))
    assert [sample.jump_out for sample in samples] == [False, False, True, True]
    assert [sample.float_surface for sample in samples] == [False, True, True, False]
    assert samples[3].surface_duration_s == 0


def test_surface_rule_has_no_unstated_speed_condition() -> None:
    points = [point(index) for index in range(4)]
    samples, _ = evaluate(points, configuration(floating_duration_s=1), speeds=[100] * 4)
    assert samples[2].float_surface and samples[2].frantic_swimming


def test_irregular_sampling_uses_seconds_not_sample_count() -> None:
    points = [point(index, time) for index, time in enumerate([0, 0.2, 0.9, 1.4, 2.1])]
    samples, events = evaluate(points, configuration(floating_duration_s=1.5))
    assert [sample.surface_duration_s for sample in samples] == pytest.approx([0, 0.2, 0.9, 1.4, 2.1])
    assert [sample.float_surface for sample in samples] == [False, False, False, False, True]
    assert events[0].start_s == events[0].end_s == 2.1


@pytest.mark.parametrize("kind", ["invalid", "skipped_frame", "time_gap"])
def test_missing_observation_resets_surface_duration_and_splits_jump_events(kind) -> None:
    points = [point(0), point(1), point(2), point(3), point(4)]
    if kind == "invalid":
        points[2] = point(2, valid=False)
    elif kind == "skipped_frame":
        points = [point(frame) for frame in [0, 1, 3, 4, 5]]
    else:
        points = [point(index, time) for index, time in enumerate([0, 1, 10, 11, 12])]
    samples, _ = evaluate(points, configuration(floating_duration_s=2))
    assert not any(sample.float_surface for sample in samples)
    above = [replace(p, Z=12) if p.is_valid else p for p in points]
    _, events = evaluate(above)
    assert len(events) == 2 and all(event.behavior == "jump_out" for event in events)
    if kind == "invalid":
        assert isnan(samples[2].surface_duration_s) and not samples[2].frantic_evaluable


def test_time_gap_is_not_differentiated_or_added_to_path() -> None:
    points = [point(index, time, xyz=(x, 0, 4)) for index, (time, x) in enumerate(
        [(0, 0), (0.5, 1), (1, 2), (10, 100), (10.5, 101), (11, 102)])]
    motion = observed_motion(points, max_gap_s=1.5, min_direction_displacement=0)
    assert motion[1].speed == motion[4].speed == 2
    assert isnan(motion[2].speed) and isnan(motion[3].speed)
    assert isnan(motion[3].step_displacement)
    assert motion[-1].cumulative_path_length == 4  # excludes the unobserved 98-unit jump


def test_three_dimensional_speed_and_angular_only_frantic_condition() -> None:
    vertical = [point(frame, xyz=(0, 0, 6 * frame)) for frame in range(3)]
    motion = observed_motion(vertical, max_gap_s=1.5, min_direction_displacement=0)
    assert motion[1].speed == 6
    assert evaluate(vertical, speeds=[sample.speed for sample in motion])[0][1].frantic_swimming
    turn = [point(index, xyz=xyz) for index, xyz in enumerate([(0, 0, 4), (1, 0, 4), (1, 1, 4)])]
    motion = observed_motion(turn, max_gap_s=1.5, min_direction_displacement=0)
    assert motion[1].turning_angle_rad == pytest.approx(pi / 2)
    assert motion[1].angular_speed_rad_s == pytest.approx(pi / 4)
    samples, events = evaluate(turn, configuration(frantic_angular_speed_rad_s=0.7),
                               [sample.speed for sample in motion], [sample.angular_speed_rad_s for sample in motion])
    assert samples[1].frantic_swimming and events[0].start_s == events[0].end_s == 1


@pytest.mark.parametrize("field,value", [
    ("coordinate_unit", "mm"), ("coordinate_frame", "tank_world"), ("data_source", "experimental"),
])
def test_threshold_units_frame_and_source_must_match(field, value) -> None:
    with pytest.raises(ValueError, match="unit/frame/data_source"):
        evaluate([replace(point(0), **{field: value})])


@pytest.mark.parametrize("changes", [
    {"max_gap_s": 0}, {"surface_tolerance": -1}, {"floating_duration_s": float("nan")},
    {"frantic_speed": float("inf")}, {"frantic_angular_speed_rad_s": -1},
    {"water_surface_z": float("nan")}, {"data_source": "real"},
])
def test_invalid_rule_configuration(changes) -> None:
    with pytest.raises(ValueError):
        configuration(**changes)


def test_feature_alignment_and_behavior_protocol() -> None:
    recognizer = RuleBehaviorRecognizer(configuration())
    with pytest.raises(ValueError, match="feature lengths"):
        recognizer.detect([point(0)], [], [0])
    assert recognizer.detect([point(0, xyz=(0, 0, 12))], [float("nan")], [float("nan")])[0].behavior == "jump_out"


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_demo_pipeline_executes_all_rules_and_preserves_provenance(tmp_path) -> None:
    config = Path("configs/synthetic_behavior.yaml")
    points = generate_behavior_demo(config)
    input_path = tmp_path / "trajectory.csv"
    export_trajectory(input_path, points)
    output = tmp_path / "analysis"
    manifest = analyze_behavior(input_path, config, output)
    assert manifest["frame_count"] == 51 and manifest["stage"] == "S6"
    assert manifest["event_counts"] == {"frantic_swimming": 1, "float_surface": 1, "jump_out": 1}
    assert manifest["input_trajectory_sha256"] == hashlib.sha256(input_path.read_bytes()).hexdigest()
    assert manifest["config_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert not manifest["behavior_accuracy_validated_on_real_data"]
    events = read_rows(output / "behavior_events.csv")
    floating = next(event for event in events if event["behavior"] == "float_surface")
    assert (float(floating["start_s"]), float(floating["end_s"])) == (36, 44)
    assert all(event["result_type"] == "rule_prediction" and event["data_source"] == "synthetic" for event in events)
    assert len(read_rows(output / "behavior_samples.csv")) == len(read_rows(output / "motion.csv")) == 51
    for filename in manifest["output_files"]:
        assert (output / filename).stat().st_size > 0


def test_csv_changed_identity_and_all_invalid_do_not_merge_or_invent_events(tmp_path) -> None:
    config = tmp_path / "behavior.yaml"
    config.write_text(yaml.safe_dump({"behavior": asdict(configuration(floating_duration_s=1))}), encoding="utf-8")
    points = [point(frame, identity="first" if frame < 3 else "second") for frame in range(8)]
    points[6] = point(6, identity="second", valid=False)
    input_path = tmp_path / "trajectory.csv"
    export_trajectory(input_path, points)
    manifest = analyze_behavior(input_path, config, tmp_path / "analysis")
    assert manifest["fish_id_count"] == 2 and manifest["event_counts"] == {"float_surface": 2}
    events = read_rows(tmp_path / "analysis/behavior_events.csv")
    assert [(event["fish_id"], float(event["start_s"]), float(event["end_s"])) for event in events] == [
        ("first", 2, 2), ("second", 5, 5),
    ]
    export_trajectory(input_path, [point(frame, identity="unassigned", valid=False) for frame in range(3)])
    manifest = analyze_behavior(input_path, config, tmp_path / "all_invalid")
    assert manifest["valid_point_count"] == 0 and manifest["event_counts"] == {}
    assert read_rows(tmp_path / "all_invalid/behavior_events.csv") == []
    assert all(row["is_valid"] == "false" for row in read_rows(tmp_path / "all_invalid/behavior_samples.csv"))


@pytest.mark.parametrize("kind", ["empty", "duplicate", "time_reversed", "invalid_boolean"])
def test_csv_reader_rejects_invalid_order_and_validity(tmp_path, kind) -> None:
    path = tmp_path / "trajectory.csv"
    points = [point(0), point(1)]
    if kind == "empty":
        points = []
    elif kind == "duplicate":
        points[1] = points[0]
    elif kind == "time_reversed":
        points[1] = replace(points[1], timestamp_s=0)
    export_trajectory(path, points)
    if kind == "invalid_boolean":
        path.write_text(path.read_text(encoding="utf-8").replace(",true,", ",unknown,"), encoding="utf-8")
    with pytest.raises(ValueError):
        read_trajectory(path)


def test_synthetic_generator_cannot_be_marked_experimental(tmp_path) -> None:
    document = yaml.safe_load(Path("configs/synthetic_behavior.yaml").read_text(encoding="utf-8"))
    document["behavior"]["data_source"] = "experimental"
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="requires data_source=synthetic"):
        generate_behavior_demo(path)
