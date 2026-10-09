import csv
import json
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest

from fish3d.interfaces import VideoFrame
from fish3d.preprocessing import OpenCVPreprocessor
from fish3d.video_config import ROI, load_video_config
from fish3d.video_io import OpenCVVideoReader, generate_synthetic_video
from fish3d.video_processing import preprocess_video


CONFIG_PATH = Path("configs/synthetic_video.yaml")


def test_video_config_rejects_bad_rois() -> None:
    config = load_video_config(CONFIG_PATH)
    assert config.mirror_roi.width == 128
    with pytest.raises(ValueError, match="overlap"):
        replace(config, real_roi=ROI(100, 0, 192, 240))
    with pytest.raises(ValueError, match="exceeds"):
        replace(config, real_roi=ROI(200, 0, 192, 240))


def test_median_hsv_and_full_frame_roi_offsets() -> None:
    config = load_video_config(CONFIG_PATH)
    image = np.full((240, 320, 3), (30, 60, 90), dtype=np.uint8)
    image[100, 50] = (255, 255, 255)
    frame = VideoFrame(4, 0.4, image, "fps_fallback", "synthetic")
    result = OpenCVPreprocessor(config).process(frame)
    assert np.array_equal(result.undistorted_bgr, image)
    assert tuple(result.median_bgr[100, 50]) == (30, 60, 90)
    assert np.array_equal(result.full_hsv, cv2.cvtColor(result.median_bgr, cv2.COLOR_BGR2HSV))
    mirror, real = result.views
    assert (mirror.view, mirror.roi_x, mirror.roi_y, mirror.image.shape) == ("mirror", 0, 0, (240, 128, 3))
    assert (real.view, real.roi_x, real.roi_y, real.image.shape) == ("real", 128, 0, (240, 192, 3))
    assert np.array_equal(real.image, result.full_hsv[:, 128:320])


def test_zero_distortion_calibration_interface(tmp_path) -> None:
    config = load_video_config(CONFIG_PATH)
    calibration = tmp_path / "camera.json"
    calibration.write_text(json.dumps({
        "camera_matrix": [[200, 0, 160], [0, 200, 120], [0, 0, 1]],
        "distortion_coefficients": [0, 0, 0, 0, 0],
        "image_width": 320,
        "image_height": 240,
    }), encoding="utf-8")
    calibrated = OpenCVPreprocessor(replace(config, calibration_file=calibration))
    image = np.full((240, 320, 3), 80, dtype=np.uint8)
    result = calibrated.process(VideoFrame(0, 0.0, image, "decoder", "synthetic"))
    assert np.array_equal(result.undistorted_bgr, image)
    with pytest.raises(ValueError, match="image size"):
        OpenCVPreprocessor(replace(config, expected_width=321, calibration_file=calibration))


def test_nonzero_distortion_changes_image(tmp_path) -> None:
    config = load_video_config(CONFIG_PATH)
    calibration = tmp_path / "camera.json"
    matrix = [[200, 0, 160], [0, 200, 120], [0, 0, 1]]
    coefficients = [0.2, 0, 0, 0, 0]
    calibration.write_text(json.dumps({
        "camera_matrix": matrix,
        "distortion_coefficients": coefficients,
        "image_width": 320,
        "image_height": 240,
    }), encoding="utf-8")
    yy, xx = np.indices((240, 320))
    checkerboard = (((xx // 10 + yy // 10) % 2) * 255).astype(np.uint8)
    image = np.repeat(checkerboard[:, :, None], 3, axis=2)
    result = OpenCVPreprocessor(replace(config, calibration_file=calibration)).process(
        VideoFrame(0, 0.0, image, "decoder", "synthetic")
    )
    expected = cv2.undistort(image, np.asarray(matrix, dtype=float), np.asarray(coefficients, dtype=float))
    assert np.array_equal(result.undistorted_bgr, expected)
    assert not np.array_equal(result.undistorted_bgr, image)


def test_reader_falls_back_when_decoder_timestamps_do_not_advance(tmp_path, monkeypatch) -> None:
    config = load_video_config(CONFIG_PATH)
    video_path = tmp_path / "placeholder.avi"
    video_path.touch()

    class Capture:
        def __init__(self) -> None:
            self.index = 0

        def isOpened(self) -> bool:
            return True

        def get(self, property_id: int) -> float:
            return 5.0 if property_id == cv2.CAP_PROP_FPS else 0.0

        def read(self):
            if self.index == 3:
                return False, None
            self.index += 1
            return True, np.zeros((240, 320, 3), dtype=np.uint8)

        def release(self) -> None:
            pass

    monkeypatch.setattr(cv2, "VideoCapture", lambda _: Capture())
    frames = list(OpenCVVideoReader(video_path, config))
    assert [frame.timestamp_s for frame in frames] == pytest.approx([0.0, 0.2, 0.4])
    assert [frame.timestamp_source for frame in frames] == ["decoder", "fps_fallback", "fps_fallback"]


def test_synthetic_video_read_and_saved_outputs(tmp_path) -> None:
    config = load_video_config(CONFIG_PATH)
    video_path = tmp_path / "synthetic_input.avi"
    generate_synthetic_video(video_path, config)
    frames = list(OpenCVVideoReader(video_path, config))
    assert len(frames) == config.synthetic_video.frame_count
    assert [frame.frame_id for frame in frames] == list(range(len(frames)))
    assert all(frame.data_source == "synthetic" for frame in frames)
    assert all(next_frame.timestamp_s > frame.timestamp_s for frame, next_frame in zip(frames, frames[1:]))
    assert frames[-1].timestamp_s == pytest.approx((len(frames) - 1) / config.synthetic_video.fps, abs=0.02)

    output = tmp_path / "processed"
    manifest = preprocess_video(video_path, CONFIG_PATH, output)
    assert manifest["frame_count"] == len(frames)
    assert manifest["data_source"] == "synthetic"
    assert manifest["calibration_applied"] is False
    with (output / "frames.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(frames)
    assert all(row["data_source"] == "synthetic" for row in rows)
    assert rows[0]["real_roi_x"] == "128"
    assert np.load(output / "full_hsv" / "frame_000000.npy").shape == (240, 320, 3)
    assert np.load(output / "mirror_hsv" / "frame_000000.npy").shape == (240, 128, 3)
    assert np.load(output / "real_hsv" / "frame_000000.npy").shape == (240, 192, 3)
    preview_path = output / "real_preview" / "frame_000000.png"
    preview = cv2.imdecode(np.frombuffer(preview_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert preview.shape == (240, 192, 3)
    for directory in manifest["output_directories"]:
        assert len(list((output / directory).iterdir())) == len(frames)

