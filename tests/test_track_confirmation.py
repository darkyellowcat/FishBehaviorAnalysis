"""SYNTHETIC transient candidates must not acquire confirmed fish segment IDs."""

from dataclasses import replace

import pytest

from fish3d.interfaces import Detection2D
from fish3d.multi_tracking import MultiFishTracker, MultiTrackingConfig


def config():
    return MultiTrackingConfig(5, 300, 0.5, 35, 30, 1.6, birth_confirmation_frames=3)


def detection(frame, x, y=100):
    return Detection2D(frame, frame / 10, "real", x, y, 20, True)


def test_single_frame_noise_never_acquires_formal_segment_id() -> None:
    tracker = MultiFishTracker("real", config())
    assert tracker.update(0, 0, [detection(0, 100)]) == []
    assert tracker.last_detection_statuses == ["tentative"]
    assert tracker.update(1, 0.1, []) == []
    for frame in (2, 3):
        assert tracker.update(frame, frame / 10, [detection(frame, 200)]) == []
    result = tracker.update(4, 0.4, [detection(4, 200)])
    assert len(result) == 1 and result[0].status == "initialized"
    assert result[0].tracked.fish_id == "real_0001"  # the transient did not consume a formal ID
    assert result[0].tracked.detection.frame_id == 4  # no retrospective predicted observations


def test_five_persistent_fish_confirm_without_transient_candidate_using_capacity() -> None:
    tracker = MultiFishTracker("real", config())
    for frame in range(3):
        fish = [detection(frame, 100 * index) for index in range(5)]
        if frame == 0:
            fish.insert(0, detection(frame, 900))
        result = tracker.update(frame, frame / 10, fish)
        assert len(result) == (5 if frame == 2 else 0)
    assert len({item.tracked.fish_id for item in result}) == 5
    missing = tracker.update(3, 0.3, [])
    assert len(missing) == 5 and all(not item.tracked.detection.is_valid for item in missing)


def test_skipped_frame_resets_tentative_confirmation_count() -> None:
    tracker = MultiFishTracker("real", config())
    assert tracker.update(0, 0, [detection(0, 100)]) == []
    assert tracker.update(2, 0.2, [detection(2, 100)]) == []
    assert tracker.update(3, 0.3, [detection(3, 100)]) == []
    assert tracker.update(4, 0.4, [detection(4, 100)])[0].status == "initialized"


def test_excess_persistent_candidates_never_exceed_confirmed_fish_capacity() -> None:
    tracker = MultiFishTracker("real", config())
    for frame in range(4):
        result = tracker.update(frame, frame / 10, [detection(frame, 100 * index) for index in range(6)])
        assert len(result) == (0 if frame < 2 else 5)
    assert tracker.last_detection_statuses.count("capacity_rejected") == 1


@pytest.mark.parametrize("value", [0, 1.5])
def test_confirmation_count_is_a_positive_integer(value) -> None:
    with pytest.raises(ValueError, match="birth_confirmation_frames"):
        replace(config(), birth_confirmation_frames=value)
