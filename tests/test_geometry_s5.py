import csv
import hashlib
import json
from dataclasses import replace
from math import isnan, sqrt
from pathlib import Path

import pytest
import yaml

from fish3d.geometry import PaperIdealReconstructor, load_geometry_config
from fish3d.interfaces import Detection2D, TrackedDetection
from fish3d.matching import MatchingConfig, SingleFishDualViewMatcher, load_matching_config
from fish3d.reconstruction_processing import reconstruct_tracks
from fish3d.schemas import TrajectoryPoint
from fish3d.tracking import missing_detection


def model(**changes):
    config = replace(load_geometry_config(Path("configs/synthetic_geometry.yaml")), **changes)
    return PaperIdealReconstructor(config, "synthetic")


def tracked(view, x, y, *, frame=1, time=0.1, identity=None):
    return TrackedDetection(Detection2D(frame, time, view, x, y, 12, True), identity or f"{view}_0001")


def test_paper_45_degree_reference_formula() -> None:
    reconstruction = model(mirror_intersection_x_px=285)
    point = reconstruction.reconstruct(tracked("real", 400, 180), tracked("mirror", 200, 180))
    assert (point.X, point.Y, point.Z) == pytest.approx((400, 180, 85))
    assert point.coordinate_unit == "model_px" and point.coordinate_frame == "paper_ideal_cartesian"
    assert point.data_source == "synthetic" and point.is_valid


def test_non_45_angle_origin_and_inverse_have_independent_reference() -> None:
    reconstruction = model(mirror_angle_deg=30, image_origin_px=(5, 10))
    point = reconstruction.reconstruct(tracked("real", 107, 65), tracked("mirror", 54, 65))
    assert (point.X, point.Y, point.Z) == pytest.approx((102, 55, 10 / sqrt(3)))
    real, mirror = reconstruction.project(point)
    assert real == pytest.approx((107, 65)) and mirror == pytest.approx((54, 65))


def test_known_3d_points_project_and_reconstruct_with_irregular_time() -> None:
    reconstruction = model(mirror_angle_deg=60, mirror_intersection_x_px=70, image_origin_px=(2, 3))
    for frame, (time, coordinates) in enumerate([
        (0, (110, 50, 24)), (0.07, (114, 55, 31)), (0.2, (120, 59, 40)), (0.45, (130, 66, 30)),
    ]):
        truth = TrajectoryPoint(frame, time, "known", *coordinates, "model_px", True,
                                "paper_ideal_cartesian", "synthetic")
        real, mirror = reconstruction.project(truth)
        result = reconstruction.reconstruct(
            tracked("real", *real, frame=frame, time=time),
            tracked("mirror", *mirror, frame=frame, time=time),
        )
        assert (result.X, result.Y, result.Z) == pytest.approx(coordinates, abs=1e-12)
        assert result.timestamp_s == time and result.frame_id == frame


def test_geometric_reference_is_independent_of_image_partition_and_not_clamped() -> None:
    # ROI boundary in the fixture is 64, but geometry may have a different reference.
    reconstruction = model(mirror_intersection_x_px=55)
    point = reconstruction.reconstruct(tracked("real", 110, 60), tracked("mirror", 60, 60))
    assert point.Z == pytest.approx(-5)
    # Negative model height is not silently clipped into a valid tank position.


def test_missing_view_produces_all_nan_coordinates() -> None:
    reconstruction = model()
    missing = TrackedDetection(missing_detection(1, 0.1, "mirror"), "mirror_0001")
    point = reconstruction.reconstruct(tracked("real", 110, 60), missing)
    assert not point.is_valid and all(isnan(value) for value in (point.X, point.Y, point.Z))
    with pytest.raises(ValueError, match="invalid"):
        reconstruction.project(point)


def test_matching_does_not_require_equal_view_local_ids_and_checks_y_gate() -> None:
    matcher = SingleFishDualViewMatcher(MatchingConfig(3))
    real = tracked("real", 110, 60, identity="real_0002")
    mirror = tracked("mirror", 40, 63, identity="mirror_0007")
    assert matcher.match(real, mirror) == (real, mirror)
    assert matcher.last_y_disparity_px == 3
    assert model().reconstruct(real, mirror).fish_id == "real_0002__mirror_0007"
    assert matcher.match(real, replace(mirror, detection=replace(mirror.detection, y_px=63.01))) is None
    assert matcher.last_status == "y_disparity_exceeded"


def test_matching_requires_exact_frame_time_and_valid_tracks() -> None:
    matcher = SingleFishDualViewMatcher(MatchingConfig(3))
    real, mirror = tracked("real", 110, 60), tracked("mirror", 40, 60)
    assert matcher.match(real, replace(mirror, detection=replace(mirror.detection, frame_id=2))) is None
    assert matcher.last_status == "frame_mismatch"
    assert matcher.match(real, replace(mirror, detection=replace(mirror.detection, timestamp_s=0.100000001))) is None
    assert matcher.last_status == "timestamp_mismatch"
    missing = TrackedDetection(missing_detection(1, 0.1, "mirror"), "mirror_0001")
    assert matcher.match(real, missing) is None and matcher.last_status == "invalid_detection"
    assert matcher.match(real, replace(mirror, fish_id="")) is None
    assert matcher.last_status == "missing_track_id"
    with pytest.raises(ValueError, match="ordered real"):
        matcher.match(mirror, real)


def test_direct_reconstruction_checks_sync_identity_and_projection_units() -> None:
    reconstruction = model()
    real, mirror = tracked("real", 110, 60), tracked("mirror", 40, 60)
    with pytest.raises(ValueError, match="same frame"):
        reconstruction.reconstruct(real, replace(mirror, detection=replace(mirror.detection, timestamp_s=0.2)))
    with pytest.raises(ValueError, match="track IDs"):
        reconstruction.reconstruct(real, replace(mirror, fish_id=""))
    point = reconstruction.reconstruct(real, mirror)
    with pytest.raises(ValueError, match="unit/frame"):
        reconstruction.project(replace(point, coordinate_unit="mm"))


@pytest.mark.parametrize("changes", [
    {"mirror_angle_deg": 0}, {"mirror_angle_deg": 90}, {"mirror_angle_deg": float("nan")},
    {"mirror_intersection_x_px": float("inf")}, {"image_origin_px": (0,)},
    {"coordinate_unit": "mm"}, {"coordinate_frame": "tank_world"},
])
def test_geometry_configuration_rejects_invalid_or_physical_labels(changes) -> None:
    with pytest.raises(ValueError):
        model(**changes)


def test_matching_configuration_loader_and_invalid_gate() -> None:
    assert load_matching_config(Path("configs/synthetic_geometry.yaml")).max_y_disparity_px == 3
    with pytest.raises(ValueError, match="nonnegative"):
        MatchingConfig(-1)


def write_fixture(tmp_path):
    document = yaml.safe_load(Path("configs/synthetic_geometry.yaml").read_text(encoding="utf-8"))
    config_path = tmp_path / "geometry.yaml"
    config_path.write_text(yaml.safe_dump(document), encoding="utf-8")
    rows = []
    times = (0, 0.1, 0.22, 0.34, 0.51, 0.9, 1.2, 1.4)
    for frame, time in enumerate(times):
        for view in ("mirror", "real"):
            if frame == 6 and view == "mirror":
                continue
            valid = frame not in (0, 7) and not (frame == 2 and view == "mirror")
            x = 40 - frame if view == "mirror" else 110 + frame
            y = 50 + frame
            if frame == 4 and view == "mirror":
                y += 5
            rows.append({
                "frame_id": frame, "timestamp_s": time + (1e-6 if frame == 3 and view == "mirror" else 0),
                "view": view, "x_px": x if valid else "NaN", "y_px": y if valid else "NaN",
                "area_px": 20 if valid else 0, "is_valid": valid,
                "fish_id": (f"{view}_0001" if frame < 5 else f"{view}_0002") if frame else "",
                "coordinate_unit": "px", "coordinate_frame": "processed_full_frame", "data_source": "synthetic",
                "roi_x": 0 if view == "mirror" else 64, "roi_y": 0, "timestamp_source": "decoder",
            })
    csv_path = tmp_path / "tracks_2d.csv"
    write_rows(csv_path, rows)
    return config_path, csv_path, rows


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_csv_pipeline_matching_failures_segment_ids_and_source_hashes(tmp_path) -> None:
    config, tracks, _ = write_fixture(tmp_path)
    output = tmp_path / "result"
    manifest = reconstruct_tracks(tracks, config, output)
    assert manifest["stage"] == "S5" and manifest["frame_count"] == 8 and manifest["valid_point_count"] == 2
    assert manifest["matching_status_counts"] == {
        "invalid_detection": 3, "matched": 2, "timestamp_mismatch": 1,
        "y_disparity_exceeded": 1, "missing_view": 1,
    }
    assert manifest["input_tracks_sha256"] == hashlib.sha256(tracks.read_bytes()).hexdigest()
    assert manifest["config_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert not manifest["metric_calibration_applied"] and not manifest["geometry_validated_on_real_data"]
    with (output / "trajectory_3d.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 8
    for row in rows:
        frame = int(row["frame_id"])
        assert row["is_valid"] == str(frame in (1, 5)).lower()
        assert row["coordinate_unit"] == "model_px" and row["data_source"] == "synthetic"
        if frame in (1, 5):
            assert tuple(float(row[key]) for key in ("X", "Y", "Z")) == pytest.approx((110 + frame, 50 + frame, 24 + frame))
        else:
            assert all(isnan(float(row[key])) for key in ("X", "Y", "Z"))
    assert rows[0]["fish_id"] == "unassigned"
    assert rows[1]["fish_id"] != rows[5]["fish_id"]
    assert (output / "trajectory_3d.png").stat().st_size > 0


@pytest.mark.parametrize("field,value,reason", [
    ("coordinate_unit", "mm", "require px"),
    ("coordinate_frame", "roi_local", "require px"),
    ("data_source", "experimental", "data_source"),
    ("roi_x", 7, "ROI origin"),
    ("x_px", 30, "full-frame ROI"),
])
def test_csv_rejects_inconsistent_units_origin_and_source(tmp_path, field, value, reason) -> None:
    config, tracks, rows = write_fixture(tmp_path)
    rows[3][field] = value  # frame 1, real view
    write_rows(tracks, rows)
    with pytest.raises(ValueError, match=reason):
        reconstruct_tracks(tracks, config, tmp_path / "result")


def test_duplicate_rows_and_decreasing_time_are_rejected(tmp_path) -> None:
    config, tracks, rows = write_fixture(tmp_path)
    write_rows(tracks, [rows[0], rows[0], *rows[1:]])
    with pytest.raises(ValueError, match="duplicate"):
        reconstruct_tracks(tracks, config, tmp_path / "result")
    rows[2]["timestamp_s"] = rows[3]["timestamp_s"] = 0
    write_rows(tracks, rows)
    with pytest.raises(ValueError, match="increase"):
        reconstruct_tracks(tracks, config, tmp_path / "result")


def test_all_missing_frames_export_without_fabricated_points(tmp_path) -> None:
    config, tracks, rows = write_fixture(tmp_path)
    for row in rows:
        row.update(x_px="NaN", y_px="NaN", area_px=0, is_valid=False, fish_id="")
    write_rows(tracks, rows)
    manifest = reconstruct_tracks(tracks, config, tmp_path / "result")
    assert manifest["valid_point_count"] == 0


def test_camera_json_interface_does_not_imply_metric_geometry(tmp_path) -> None:
    config, tracks, _ = write_fixture(tmp_path)
    calibration = {
        "camera_matrix": [[200, 0, 80], [0, 200, 60], [0, 0, 1]],
        "distortion_coefficients": [0, 0, 0, 0, 0], "image_width": 160, "image_height": 120,
    }
    camera_path = tmp_path / "camera.json"
    camera_path.write_text(json.dumps(calibration), encoding="utf-8")
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    document["preprocessing"]["calibration_file"] = "camera.json"
    config.write_text(yaml.safe_dump(document), encoding="utf-8")
    manifest = reconstruct_tracks(tracks, config, tmp_path / "result")
    metadata = manifest["configured_camera_calibration"]
    assert metadata["sha256"] == hashlib.sha256(camera_path.read_bytes()).hexdigest()
    assert not metadata["used_for_metric_reconstruction"]
    assert manifest["coordinate_unit"] == "model_px"
    calibration["image_width"] = 640
    camera_path.write_text(json.dumps(calibration), encoding="utf-8")
    with pytest.raises(ValueError, match="image size"):
        reconstruct_tracks(tracks, config, tmp_path / "result")
