import csv
import json
from dataclasses import replace
from math import cos, exp, radians
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from fish3d.foreground_processing import segment_video
from fish3d.interfaces import ViewFrame
from fish3d.lbadaptive_som import (
    LBAdaptiveSOM, hsv_distance_squared, load_som_config, normalize_opencv_hsv,
)
from fish3d.video_config import load_video_config
from fish3d.video_io import generate_synthetic_video


def config(**changes):
    return replace(load_som_config(Path("configs/synthetic_som.yaml")), **changes)


def view(frame_id, pixels, label="real"):
    image = np.asarray(pixels, dtype=np.uint8)
    return ViewFrame(frame_id, frame_id * 0.1, label, image, 10, 20)


def test_hsv_scale_and_squared_periodic_distance() -> None:
    normalized = normalize_opencv_hsv(np.array([[[179, 255, 255]]], dtype=np.uint8))
    assert normalized[0, 0] == pytest.approx((358, 1, 1))
    red = np.array((0.0, 1.0, 1.0))
    wrap = np.array((358.0, 1.0, 1.0))
    assert float(hsv_distance_squared(red, wrap)) == pytest.approx(2 - 2 * cos(radians(2)))
    assert float(hsv_distance_squared(red, np.array((90.0, 1.0, 1.0)))) == pytest.approx(2.0)


def test_initialization_and_static_background() -> None:
    model = LBAdaptiveSOM(config())
    first = model.segment(view(0, [[[20, 120, 180], [40, 100, 160]]]))
    assert model.weights_hsv.shape == (3, 6, 3)
    assert np.count_nonzero(first.mask) == 0
    assert model.last_stats["phase"] == "initialization"
    assert first.roi_x == 10 and first.roi_y == 20
    for frame_id in range(1, 4):
        result = model.segment(view(frame_id, [[[20, 120, 180], [40, 100, 160]]]))
        assert np.count_nonzero(result.mask) == 0


def test_learning_to_online_threshold_transition() -> None:
    model = LBAdaptiveSOM(config(mapping_size=1, learning_frames=2, learning_rate=1.0))
    model.segment(view(0, [[[0, 0, 100]]]))
    assert model.segment(view(1, [[[0, 0, 140]]])).mask[0, 0] == 0
    assert model.last_stats["phase"] == "learning"
    assert model.last_stats["threshold_squared"] == 0.1
    assert model.segment(view(2, [[[0, 0, 180]]])).mask[0, 0] == 255
    assert model.last_stats["phase"] == "online"
    assert model.last_stats["threshold_squared"] == 0.01


def test_foreground_is_not_learned() -> None:
    model = LBAdaptiveSOM(config(learning_frames=1))
    model.segment(view(0, [[[0, 0, 30]]]))
    before = model.weights_hsv.copy()
    result = model.segment(view(1, [[[60, 255, 255]]]))
    assert result.mask[0, 0] == 255
    assert np.array_equal(model.weights_hsv, before)


def test_shadow_is_background_without_model_update() -> None:
    model = LBAdaptiveSOM(config(learning_frames=1))
    model.segment(view(0, [[[50, 153, 200]]]))
    before = model.weights_hsv.copy()
    shadow = model.segment(view(1, [[[50, 153, 150]]]))
    assert shadow.mask[0, 0] == 0
    assert model.last_stats["shadow_pixels"] == 1
    assert model.last_stats["background_updates"] == 0
    assert np.array_equal(model.weights_hsv, before)
    changed_hue = model.segment(view(2, [[[100, 153, 150]]]))
    assert changed_hue.mask[0, 0] == 255


def test_black_reference_does_not_divide_by_zero() -> None:
    model = LBAdaptiveSOM(config(learning_frames=1))
    model.segment(view(0, [[[0, 0, 0]]]))
    with np.errstate(divide="raise", invalid="raise"):
        assert model.segment(view(1, [[[0, 0, 255]]])).mask[0, 0] == 255


def test_gaussian_update_crosses_input_pixel_blocks() -> None:
    model = LBAdaptiveSOM(config(learning_frames=1))
    model.segment(view(0, [[[0, 0, 100], [0, 0, 100]]]))
    # The best match is on the right edge of the first pixel's 3x3 block.
    model.weights_hsv[1, 2, 2] = 110 / 255
    result = model.segment(view(1, [[[0, 0, 110], [90, 255, 255]]]))
    assert result.mask.tolist() == [[0, 255]]
    expected = 100 / 255 + 0.05 * exp(-0.5) * (10 / 255)
    assert model.weights_hsv[1, 3, 2] == pytest.approx(expected)
    assert model.weights_hsv[1, 4, 2] == pytest.approx(100 / 255)


def test_neighborhood_clips_at_model_boundary() -> None:
    model = LBAdaptiveSOM(config(learning_frames=1))
    model.segment(view(0, [[[0, 0, 100]]]))
    model.segment(view(1, [[[0, 0, 110]]]))
    assert model.weights_hsv[0, 0, 2] == pytest.approx((100 + 0.05 * 10) / 255)
    assert model.weights_hsv[1, 1, 2] == pytest.approx((100 + 0.05 * exp(-1) * 10) / 255)
    assert model.weights_hsv[2, 2, 2] == pytest.approx(100 / 255)


def test_first_frame_object_is_incorporated_into_background() -> None:
    model = LBAdaptiveSOM(config())
    image = [[[0, 0, 30], [60, 255, 255]]]
    assert not model.segment(view(0, image)).mask.any()
    assert not model.segment(view(1, image)).mask.any()


def test_hue_wrap_matches_but_keeps_printed_linear_update() -> None:
    model = LBAdaptiveSOM(config(mapping_size=1, learning_frames=1))
    model.segment(view(0, [[[0, 255, 255]]]))
    assert model.segment(view(1, [[[179, 255, 255]]])).mask[0, 0] == 0
    assert model.weights_hsv[0, 0, 0] == pytest.approx(0.05 * 358)


def test_threshold_equality_counts_as_background() -> None:
    model = LBAdaptiveSOM(config(mapping_size=1, epsilon_learning=1, epsilon_online=1))
    model.segment(view(0, [[[0, 0, 0]]]))
    assert model.segment(view(1, [[[0, 0, 255]]])).mask[0, 0] == 0


def test_input_and_state_contracts_are_checked() -> None:
    with pytest.raises(ValueError, match="uint8"):
        normalize_opencv_hsv(np.zeros((1, 1, 3), dtype=float))
    with pytest.raises(ValueError, match="0..179"):
        normalize_opencv_hsv(np.array([[[180, 0, 0]]], dtype=np.uint8))
    model = LBAdaptiveSOM(config())
    model.segment(view(0, [[[0, 0, 30]]]))
    with pytest.raises(ValueError, match="increase"):
        model.segment(view(0, [[[0, 0, 30]]]))
    with pytest.raises(ValueError, match="geometry"):
        model.segment(view(1, [[[0, 0, 30]]], label="mirror"))
    with pytest.raises(ValueError, match="odd"):
        config(mapping_size=2)
    with pytest.raises(ValueError, match="finite"):
        config(learning_rate=float("nan"))


def test_synthetic_video_pipeline_and_saved_model(tmp_path) -> None:
    document = yaml.safe_load(Path("configs/synthetic_som.yaml").read_text(encoding="utf-8"))
    document["video"].update(expected_width=64, expected_height=48)
    document["rois"] = {
        "mirror": {"x": 0, "y": 0, "width": 24, "height": 48},
        "real": {"x": 24, "y": 0, "width": 40, "height": 48},
    }
    document["synthetic_video"].update(
        frame_count=6, background_only_frames=2, fish_axes_px=[3, 2], horizontal_motion_px=4,
    )
    document["som"]["learning_frames"] = 2
    path = tmp_path / "synthetic_som.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    video_path = tmp_path / "synthetic.avi"
    generate_synthetic_video(video_path, load_video_config(path))
    output = tmp_path / "result"
    manifest = segment_video(video_path, path, output)
    assert manifest["data_source"] == "synthetic" and manifest["frame_count"] == 6
    with (output / "segmentation.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 12
    assert all(row["data_source"] == "synthetic" for row in rows)
    assert rows[0]["phase"] == "initialization"
    assert rows[2]["phase"] == "learning"
    assert rows[4]["phase"] == "online"
    assert any(int(row["foreground_pixels"]) > 0 for row in rows[4:])
    for directory in manifest["output_directories"]:
        assert len(list((output / directory).iterdir())) == 6
    full = cv2.imdecode(np.frombuffer((output / "masks/full/frame_000003.png").read_bytes(), dtype=np.uint8), 0)
    real = cv2.imdecode(np.frombuffer((output / "masks/real/frame_000003.png").read_bytes(), dtype=np.uint8), 0)
    assert set(np.unique(full)) <= {0, 255}
    assert np.array_equal(full[:, 24:], real)
    with np.load(output / "background_model_real.npz", allow_pickle=False) as state:
        assert state["weights_hsv"].shape == (48 * 3, 40 * 3, 3)
        metadata = json.loads(str(state["metadata"]))
        assert metadata["processed_frames"] == 6
        assert metadata["data_source"] == "synthetic"
        assert metadata["roi_x"] == 24
