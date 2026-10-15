"""SYNTHETIC fish/bubble fixtures test the optional engineering shape filter."""

from dataclasses import replace

import cv2
import numpy as np
import pytest

from fish3d.centroid import CentroidConfig, ConnectedComponentCentroidExtractor
from fish3d.interfaces import ForegroundMask


def fixture():
    image = np.zeros((180, 250), dtype=np.uint8)
    for index in range(5):
        cv2.ellipse(image, (25 + 45 * index, 35), (12, 3), index * 30, 0, 360, 255, -1)
    for index in range(10):
        cv2.circle(image, (20 + 23 * index, 100), 6, 255, -1)
    return ForegroundMask(7, 0.7, "real", image, 90, 80)


def test_rotated_fish_survive_while_round_bubbles_are_rejected() -> None:
    config = CentroidConfig(10, 200, 0, 0, 8)
    baseline = ConnectedComponentCentroidExtractor(config)
    assert len(baseline.extract_all(fixture())) == 15
    filtered = ConnectedComponentCentroidExtractor(replace(config, min_axis_ratio=2.0))
    found = filtered.extract_all(fixture())
    assert len(found) == 5
    assert sorted((round(point.x_px), round(point.y_px)) for point in found) == [
        (115 + 45 * index, 115) for index in range(5)
    ]
    assert filtered.last_area_candidate_count == 15
    assert filtered.last_shape_rejected_count == 10
    assert sum(feature["shape_accepted"] for feature in filtered.last_component_features) == 5


def test_default_preserves_round_targets_and_explicitly_documents_recall_tradeoff() -> None:
    config = CentroidConfig(10, 200, 0, 0, 8)
    mask = fixture()
    baseline = ConnectedComponentCentroidExtractor(config)
    assert len(baseline.extract_all(mask)) == 15
    assert baseline.last_shape_rejected_count == 0
    assert baseline.extract(mask).is_valid  # Single-fish baseline stays available.


@pytest.mark.parametrize("value", [0.9, float("nan"), float("inf")])
def test_axis_ratio_configuration_is_finite_and_at_least_one(value) -> None:
    with pytest.raises(ValueError, match="min_axis_ratio"):
        replace(CentroidConfig(10, 200, 0, 0, 8), min_axis_ratio=value)


def test_thin_and_single_pixel_components_have_defined_filter_behavior() -> None:
    image = np.zeros((12, 20), dtype=np.uint8)
    image[2, 2:10] = 255
    image[8, 16] = 255
    mask = ForegroundMask(0, 0, "real", image, 0, 0)
    model = ConnectedComponentCentroidExtractor(CentroidConfig(1, 50, 0, 0, 8, min_axis_ratio=2))
    found = model.extract_all(mask)
    assert len(found) == 1 and found[0].area_px == 8
    # Degenerate line is elongated; a singleton has no measurable direction.
    assert model.last_component_features[0]["axis_ratio"] == float("inf")
