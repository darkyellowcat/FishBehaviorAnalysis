import csv
import hashlib
import json
from dataclasses import replace
from math import isnan
from pathlib import Path

import numpy as np
import pytest
import yaml

from fish3d.centroid import CentroidConfig, ConnectedComponentCentroidExtractor
from fish3d.interfaces import Detection2D, ForegroundMask
from fish3d.multi_tracking import MultiFishTracker, MultiTrackingConfig, load_multi_tracking_config
from fish3d.multi_tracking_processing import (
    MultiProcessingConfig, generate_multi_video, restore_coordinates, track_multi_video,
)
from fish3d.video_config import ROI


def tracker(**changes):
    return MultiFishTracker("real", replace(MultiTrackingConfig(5, 10, 3, 10, 4, 1.5), **changes))


def detection(frame, time, x, y=0, area=12):
    return Detection2D(frame, time, "real", x, y, area, True)


def valid_positions(observations):
    return {item.tracked.fish_id: (item.tracked.detection.x_px, item.tracked.detection.y_px)
            for item in observations if item.tracked.detection.is_valid}


def test_all_components_retained_and_single_fish_selection_unchanged() -> None:
    image = np.zeros((30, 30), dtype=np.uint8)
    for index in range(5):
        image[2 + index * 5:4 + index * 5, 2:5] = 255
    image[0, 20] = 255  # filtered noise
    mask = ForegroundMask(0, 0, "real", image, 90, 80)
    extractor = ConnectedComponentCentroidExtractor(CentroidConfig(4, 20, 0, 0, 8))
    points = extractor.extract_all(mask)
    assert len(points) == extractor.last_candidate_count == 5
    assert [(point.x_px, point.y_px) for point in points] == [(93, 82.5 + 5 * index) for index in range(5)]
    assert extractor.extract(mask) == points[0]
    assert extractor.extract_all(ForegroundMask(1, 1, "real", np.zeros_like(image), 0, 0)) == []


def test_five_tracks_stay_independent_under_shuffled_detection_order_and_xy_motion() -> None:
    instance = tracker()
    first = instance.update(0, 0, [detection(0, 0, 10 * index, 20 * index) for index in range(5)])
    identities = list(valid_positions(first))
    for frame, time in [(1, 0.25), (2, 0.9), (3, 1.4)]:
        candidates = [detection(frame, time, 10 * index + 3 * time, 20 * index + 4 * time) for index in reversed(range(5))]
        positions = valid_positions(instance.update(frame, time, candidates))
        assert len(positions) == 5
        for index, identity in enumerate(identities):
            assert positions[identity] == pytest.approx((10 * index + 3 * time, 20 * index + 4 * time))


def test_population_count_is_a_cap_not_fabricated_observations() -> None:
    instance = tracker()
    assert instance.update(0, 0, []) == []
    result = instance.update(1, 1, [detection(1, 1, 0)])
    assert len(result) == 1
    result = instance.update(2, 2, [detection(2, 2, 50 * index) for index in range(7)])
    assert len(valid_positions(result)) == 5
    assert instance.last_detection_statuses.count("capacity_rejected") == 2


def test_prediction_preserves_ids_through_crossing_and_large_merged_blob() -> None:
    instance = tracker()
    first = instance.update(0, 0, [detection(0, 0, 10), detection(0, 0, 20)])
    left, right = list(valid_positions(first))
    instance.update(1, 1, [detection(1, 1, 16), detection(1, 1, 14)])
    # Predictions are 18 and 12: a shared large component near both is withheld.
    merged = instance.update(2, 2, [detection(2, 2, 15, area=24)])
    assert all(item.status == "occluded" for item in merged)
    assert instance.last_detection_statuses == ["merged_candidate"]
    assert all(not item.tracked.detection.is_valid and isnan(item.tracked.detection.x_px) for item in merged)
    result = instance.update(3, 3, [detection(3, 3, 8), detection(3, 3, 22)])
    assert valid_positions(result) == {left: (22, 0), right: (8, 0)}


def test_global_assignment_maximizes_feasible_matches_before_distance() -> None:
    instance = tracker(max_speed_px_s=5, merge_radius_px=1)
    first = instance.update(0, 0, [detection(0, 0, 0), detection(0, 0, 5)])
    left, right = list(valid_positions(first))
    result = instance.update(1, 1, [detection(1, 1, 4), detection(1, 1, 9)])
    assert valid_positions(result) == {left: (4, 0), right: (9, 0)}


def test_short_gap_keeps_id_and_long_gap_ends_segment_without_prediction_export() -> None:
    instance = tracker(expected_fish_count=1, max_gap_s=0.5)
    identity = instance.update(0, 0, [detection(0, 0, 0)])[0].tracked.fish_id
    result = instance.update(1, 0.2, [])
    assert result[0].tracked.fish_id == identity and result[0].status == "missing"
    assert not result[0].tracked.detection.is_valid and isnan(result[0].tracked.detection.y_px)
    result = instance.update(2, 0.4, [detection(2, 0.4, 3)])
    assert result[0].tracked.fish_id == identity and result[0].status == "tracked"
    result = instance.update(3, 1, [detection(3, 1, 100)])
    assert result[0].status == "lost" and result[0].tracked.fish_id == identity
    assert result[1].status == "initialized" and result[1].tracked.fish_id != identity


def test_prediction_gate_and_speed_gate_reject_impossible_jumps() -> None:
    instance = tracker(expected_fish_count=1, max_speed_px_s=10)
    identity = instance.update(0, 0, [detection(0, 0, 0)])[0].tracked.fish_id
    result = instance.update(1, 0.1, [detection(1, 0.1, 10)])
    assert result[0].status == "missing" and result[0].tracked.fish_id == identity
    assert instance.last_detection_statuses == ["capacity_rejected"]
    instance = tracker(expected_fish_count=1, max_speed_px_s=100, max_prediction_error_px=2)
    instance.update(0, 0, [detection(0, 0, 0)])
    assert instance.update(1, 1, [detection(1, 1, 3)])[0].status == "missing"


def test_input_validation_happens_before_mutating_tracker() -> None:
    instance = tracker()
    with pytest.raises(ValueError, match="nonnegative"):
        instance.update(0, -0.1, [])
    with pytest.raises(ValueError, match="view/frame/timestamp"):
        instance.update(0, 0, [replace(detection(0, 0, 1), view="mirror")])
    with pytest.raises(ValueError, match="finite"):
        instance.update(0, 0, [replace(detection(0, 0, 1), x_px=float("nan"))])
    instance.update(0, 0, [])
    with pytest.raises(ValueError, match="increase"):
        instance.update(0, 0.1, [])


@pytest.mark.parametrize("changes", [
    {"expected_fish_count": 0}, {"max_speed_px_s": float("nan")}, {"max_gap_s": 0},
    {"max_prediction_error_px": -1}, {"merge_radius_px": 0}, {"merge_area_ratio": 1},
])
def test_invalid_association_configuration(changes) -> None:
    with pytest.raises(ValueError):
        tracker(**changes)


@pytest.mark.parametrize("changes", [{"view": "left"}, {"processing_scale": 0},
                                    {"processing_scale": float("nan")}, {"max_frames": 0}])
def test_invalid_preview_configuration(changes) -> None:
    with pytest.raises(ValueError):
        replace(MultiProcessingConfig("real", 0.25, 60, "preliminary"), **changes)


def test_resized_local_centers_return_to_original_full_frame_units() -> None:
    result = restore_coordinates(detection(3, 0.3, 2, 3, 10), ROI(90, 80, 370, 510), 0.25, 0.5)
    assert (result.x_px, result.y_px, result.area_px) == (99.5, 86.5, 80)
    assert (result.frame_id, result.timestamp_s, result.view) == (3, 0.3, "real")


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_five_fish_som_pipeline_missing_coordinates_ids_and_provenance(tmp_path) -> None:
    config = Path("configs/synthetic_multi_tracking.yaml")
    video, truth = tmp_path / "synthetic.avi", tmp_path / "truth.csv"
    generate_multi_video(video, config, truth)
    output = tmp_path / "result"
    manifest = track_multi_video(video, config, output)
    assert manifest["frame_count"] == 20
    assert manifest["valid_track_count_histogram"] == {0: 3, 5: 15, 4: 2}
    assert manifest["track_status_counts"] == {"initialized": 5, "tracked": 78, "missing": 2}
    assert manifest["input_sha256"] == hashlib.sha256(video.read_bytes()).hexdigest()
    assert manifest["config_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert not manifest["physical_identity_validated"] and not manifest["reconstruction_applied"]
    assert not manifest["accuracy_validated_with_manual_labels"]
    tracks, expected = read_rows(output / "tracks_2d.csv"), read_rows(truth)
    assert len(expected) == 100 and len(tracks) == 85
    # Segment numbers follow measured area ordering, not the fixture's fish labels.
    reference = [row for row in expected if row["frame_id"] == "3"]
    identities = {}
    for row in tracks:
        if row["status"] == "initialized":
            known = min(reference, key=lambda truth: (
                (float(truth["x_px"]) - float(row["x_px"])) ** 2
                + (float(truth["y_px"]) - float(row["y_px"])) ** 2))
            identities[row["fish_id"]] = known["fixture_id"]
    assert len(set(identities.values())) == 5
    by_fixture = {(row["frame_id"], row["fixture_id"]): row for row in expected}
    for row in tracks:
        assert row["data_source"] == "synthetic" and row["coordinate_unit"] == "px"
        frame = int(row["frame_id"])
        known = by_fixture[row["frame_id"], identities[row["fish_id"]]]
        if row["is_valid"] == "True":
            assert known["is_valid"] == "true"
            assert (float(row["x_px"]), float(row["y_px"])) == pytest.approx(
                (float(known["x_px"]), float(known["y_px"])), abs=1.0)
        else:
            assert frame in (8, 9) and known["is_valid"] == "false"
            assert isnan(float(row["x_px"])) and isnan(float(row["y_px"]))
    for filename in manifest["output_files"]:
        assert (output / filename).stat().st_size > 0
    for directory in manifest["output_directories"]:
        assert len(list((output / directory).glob("*.png"))) == 20
    stored = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert stored["data_source"] == "synthetic"


def test_preview_frame_limit_and_scaling_are_explicit_and_not_relabelled(tmp_path) -> None:
    document = yaml.safe_load(Path("configs/synthetic_multi_tracking.yaml").read_text(encoding="utf-8"))
    document["multi_processing"].update(max_frames=6, processing_scale=0.5)
    document["centroid"].update(min_area_px=2, max_area_px=40)
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(document), encoding="utf-8")
    video = tmp_path / "synthetic.avi"
    generate_multi_video(video, config, tmp_path / "truth.csv")
    manifest = track_multi_video(video, config, tmp_path / "result")
    assert manifest["frame_count"] == 6 and manifest["scaled_mask_size"] == [48, 60]
    assert manifest["effective_scale_xy"] == [0.5, 0.5]
    assert manifest["data_source"] == "synthetic"
    tracks = read_rows(tmp_path / "result/tracks_2d.csv")
    assert len(tracks) == 15
    assert {row["coordinate_frame"] for row in tracks} == {"processed_full_frame"}


def test_experimental_configuration_uses_confirmed_view_and_does_not_generate_fake_video(tmp_path) -> None:
    config = Path("configs/experiment_001_multi_preview.yaml")
    assert load_multi_tracking_config(config).expected_fish_count == 5
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    assert document["rois"]["real"]["x"] < document["rois"]["mirror"]["x"]
    assert document["multi_processing"]["roi_status"] == "preliminary_from_sampled_images"
    with pytest.raises(ValueError, match="requires data_source=synthetic"):
        generate_multi_video(tmp_path / "fake.avi", config, tmp_path / "fake_truth.csv")
    assert not (tmp_path / "fake.avi").exists()
