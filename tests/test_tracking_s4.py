import csv
import json
from dataclasses import replace
from math import hypot, isnan, pi, sin
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from fish3d.centroid import (
    CentroidConfig, ConnectedComponentCentroidExtractor, load_centroid_config,
)
from fish3d.interfaces import Detection2D, ForegroundMask
from fish3d.tracking import SingleFishTracker, TrackingConfig, load_tracking_config, missing_detection
from fish3d.tracking_processing import track_video
from fish3d.video_config import load_video_config
from fish3d.video_io import generate_synthetic_video


def extractor(**changes):
    return ConnectedComponentCentroidExtractor(replace(CentroidConfig(1, 1000, 0, 0, 8), **changes))


def mask(image, *, roi_x=10, roi_y=20):
    return ForegroundMask(7, 0.7, "real", image, roi_x, roi_y)


def detection(frame, time, x, y=0.0, view="real"):
    return Detection2D(frame, time, view, x, y, 12, True)


def test_pixel_mean_and_full_frame_offset() -> None:
    image = np.zeros((12, 12), dtype=np.uint8)
    image[6:9, 4:9] = 255
    result = extractor().extract(mask(image))
    assert result.x_px == 16 and result.y_px == 27 and result.area_px == 15
    assert (result.frame_id, result.timestamp_s, result.view) == (7, 0.7, "real")


def test_hole_is_excluded_from_pixel_mass() -> None:
    image = np.zeros((6, 6), dtype=np.uint8)
    image[1:4, 1:5] = 255
    image[1, 1] = 0
    result = extractor().extract(mask(image, roi_x=0, roi_y=0))
    assert result.area_px == 11
    assert (result.x_px, result.y_px) == pytest.approx((29 / 11, 23 / 11))


def test_noise_area_filter_largest_component_and_tie() -> None:
    image = np.zeros((14, 14), dtype=np.uint8)
    image[0, 0] = 255  # below minimum area
    image[1:3, 3:6] = 255
    image[6:8, 1:4] = 255  # equal area: later y loses
    image[9:14, 8:14] = 255  # above maximum area
    model = extractor(min_area_px=4, max_area_px=10)
    result = model.extract(mask(image, roi_x=0, roi_y=0))
    assert model.last_candidate_count == 2
    assert (result.x_px, result.y_px, result.area_px) == (4, 1.5, 6)
    image[6:9, 1:4] = 255
    assert model.extract(mask(image)).area_px == 9


def test_empty_or_filtered_mask_returns_none_and_origin_is_valid() -> None:
    image = np.zeros((4, 4), dtype=np.uint8)
    model = extractor(min_area_px=2)
    assert model.extract(mask(image)) is None
    image[0, 0] = 255
    assert model.extract(mask(image)) is None
    result = extractor().extract(mask(image, roi_x=0, roi_y=0))
    assert result.is_valid and (result.x_px, result.y_px) == (0, 0)


def test_morphology_removes_noise_fills_hole_without_mutating_input() -> None:
    image = np.zeros((16, 16), dtype=np.uint8)
    image[2:11, 2:11] = 255
    image[6, 6] = 0
    image[14, 14] = 255
    original = image.copy()
    model = extractor(opening_kernel=3, closing_kernel=3)
    assert model.extract(mask(image)) is not None
    assert model.last_cleaned_mask[14, 14] == 0
    assert model.last_cleaned_mask[6, 6] == 255
    assert np.array_equal(image, original)


def test_connectivity_and_mask_validation() -> None:
    image = np.diag(np.array([255, 255, 0], dtype=np.uint8))
    assert extractor(connectivity=8).extract(mask(image)).area_px == 2
    assert extractor(connectivity=4).extract(mask(image)).area_px == 1
    with pytest.raises(ValueError, match="uint8"):
        extractor().extract(mask(image.astype(float)))
    image[0, 0] = 1
    with pytest.raises(ValueError, match="0/255"):
        extractor().extract(mask(image))


def test_stationary_and_nonuniform_time_association_uses_xy() -> None:
    tracker = SingleFishTracker("real", TrackingConfig(5, 2))
    results = tracker.track([
        detection(0, 0, 0), detection(1, 0.05, 0), detection(7, 1.05, 3, 4),
    ])
    assert all(result.detection.is_valid for result in results)
    assert {result.fish_id for result in results} == {"real_0001"}
    # Vertical movement is gated too, using actual seconds rather than frame IDs.
    rejected = tracker.update(detection(8, 1.15, 3, 5))
    assert not rejected.detection.is_valid and tracker.last_status == "rejected"


def test_short_missing_gap_keeps_id_without_predicted_coordinates() -> None:
    tracker = SingleFishTracker("real", TrackingConfig(10, 1))
    first = tracker.update(detection(0, 0, 0))
    missing = tracker.update(missing_detection(1, 0.25, "real"))
    assert missing.fish_id == first.fish_id
    assert not missing.detection.is_valid and isnan(missing.detection.x_px)
    assert tracker.last_status == "missing"
    recovered = tracker.update(detection(2, 0.5, 4))
    assert recovered.fish_id == first.fish_id and recovered.detection.is_valid


def test_long_gap_starts_new_view_local_segment() -> None:
    tracker = SingleFishTracker("real", TrackingConfig(10, 0.5))
    first = tracker.update(detection(0, 0, 0))
    missing = tracker.update(missing_detection(1, 0.51, "real"))
    assert missing.fish_id == "" and tracker.last_status == "uninitialized"
    recovered = tracker.update(detection(2, 0.8, 100))
    assert recovered.fish_id == "real_0002" and recovered.fish_id != first.fish_id
    mirror = SingleFishTracker("mirror", TrackingConfig(10, 0.5))
    assert mirror.update(detection(0, 0, 0, view="mirror")).fish_id == "mirror_0001"


def test_rejected_jump_does_not_move_association_reference() -> None:
    tracker = SingleFishTracker("real", TrackingConfig(20, 1))
    tracker.update(detection(0, 0, 0))
    rejected = tracker.update(detection(1, 0.05, 10))
    assert tracker.last_status == "rejected"
    assert not rejected.detection.is_valid and isnan(rejected.detection.y_px)
    assert tracker.update(detection(2, 0.2, 3)).detection.is_valid
    assert tracker.last_status == "tracked"


def test_tracker_input_contract_and_empty_initialization() -> None:
    tracker = SingleFishTracker("real", TrackingConfig(10, 1))
    result = tracker.update(missing_detection(0, 0, "real"))
    assert result.fish_id == "" and not result.detection.is_valid
    with pytest.raises(ValueError, match="increase"):
        tracker.update(detection(0, 0.1, 1))
    with pytest.raises(ValueError, match="increase"):
        tracker.update(detection(1, 0, 1))
    with pytest.raises(ValueError, match="view"):
        tracker.update(detection(1, 0.1, 1, view="mirror"))
    with pytest.raises(ValueError, match="finite"):
        tracker.update(detection(1, 0.1, float("nan")))
    with pytest.raises(ValueError, match="NaN"):
        tracker.update(Detection2D(1, 0.1, "real", 0, 0, 0, False))


def test_s4_configuration_and_missing_frame_validation() -> None:
    path = Path("configs/synthetic_tracking.yaml")
    assert load_centroid_config(path).opening_kernel == 3
    assert load_tracking_config(path).max_speed_px_s == 80
    synthetic = load_video_config(path).synthetic_video
    assert synthetic.missing_frame_ids == (8, 9)
    with pytest.raises(ValueError, match="within"):
        replace(synthetic, missing_frame_ids=(18,))
    with pytest.raises(ValueError, match="duplicates"):
        replace(synthetic, missing_frame_ids=(8, 8))
    with pytest.raises(ValueError, match="area"):
        CentroidConfig(10, 5, 0, 0, 8)
    with pytest.raises(ValueError, match="odd"):
        CentroidConfig(1, 10, 2, 0, 8)
    with pytest.raises(ValueError, match="connectivity"):
        CentroidConfig(1, 10, 0, 0, 6)
    with pytest.raises(ValueError, match="finite"):
        TrackingConfig(float("nan"), 1)


def test_synthetic_s4_pipeline_centroids_gaps_and_exports(tmp_path) -> None:
    document = yaml.safe_load(Path("configs/synthetic_tracking.yaml").read_text(encoding="utf-8"))
    document["video"].update(expected_width=80, expected_height=64)
    document["rois"] = {
        "mirror": {"x": 0, "y": 0, "width": 32, "height": 64},
        "real": {"x": 32, "y": 0, "width": 48, "height": 64},
    }
    document["synthetic_video"].update(
        frame_count=8, background_only_frames=2, missing_frame_ids=[4],
        fish_axes_px=[4, 3], horizontal_motion_px=4,
    )
    document["som"]["learning_frames"] = 2
    document["centroid"].update(min_area_px=10, max_area_px=120)
    path = tmp_path / "synthetic_tracking.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    video_path = tmp_path / "synthetic.avi"
    generate_synthetic_video(video_path, load_video_config(path))
    output = tmp_path / "result"
    manifest = track_video(video_path, path, output)
    assert manifest["stage"] == "S4" and manifest["data_source"] == "synthetic"
    assert manifest["frame_count"] == 8
    assert manifest["valid_tracking_observations"] == {"mirror": 5, "real": 5}
    assert manifest["rejected_observations"] == {"mirror": 0, "real": 0}
    for filename in ("detections.csv", "tracks_2d.csv"):
        with (output / filename).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 16
        for row in rows:
            frame = int(row["frame_id"])
            valid = row["is_valid"] == "True"
            assert row["data_source"] == "synthetic" and row["coordinate_unit"] == "px"
            assert valid == (frame not in (0, 1, 4))
            if not valid:
                assert isnan(float(row["x_px"])) and isnan(float(row["y_px"]))
            else:
                offset = round(4 * sin(2 * pi * frame / 8))
                expected_x = 16 - offset if row["view"] == "mirror" else 56 + offset
                assert hypot(float(row["x_px"]) - expected_x, float(row["y_px"]) - 32) < 1.5
        if filename == "tracks_2d.csv":
            for view in ("mirror", "real"):
                ids = {row["fish_id"] for row in rows if row["view"] == view and row["fish_id"]}
                assert ids == {f"{view}_0001"}
            assert all(row["status"] == "missing" for row in rows if row["frame_id"] == "4")
    for directory in manifest["output_directories"]:
        assert len(list((output / directory).glob("*.png"))) == 8
    assert (output / "tracks_2d.png").stat().st_size > 0
    saved = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert saved["config_snapshot"]["synthetic_video"]["missing_frame_ids"] == [4]
