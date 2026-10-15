"""Multi-fish 2D association: prediction, gated assignment, and missing observations."""

from dataclasses import dataclass
from math import hypot, isfinite
from pathlib import Path
from typing import Sequence

import numpy as np
import yaml
from scipy.optimize import linear_sum_assignment

from fish3d.interfaces import Detection2D, TrackedDetection
from fish3d.schemas import View
from fish3d.tracking import missing_detection


@dataclass(frozen=True, slots=True)
class MultiTrackingConfig:
    expected_fish_count: int
    max_speed_px_s: float
    max_gap_s: float
    max_prediction_error_px: float
    merge_radius_px: float
    merge_area_ratio: float
    birth_confirmation_frames: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.expected_fish_count, int) or self.expected_fish_count < 1:
            raise ValueError("expected_fish_count must be a positive integer")
        for name in ("max_speed_px_s", "max_gap_s", "max_prediction_error_px", "merge_radius_px"):
            if not isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not isfinite(self.merge_area_ratio) or self.merge_area_ratio <= 1:
            raise ValueError("merge_area_ratio must be finite and greater than one")
        if not isinstance(self.birth_confirmation_frames, int) or self.birth_confirmation_frames < 1:
            raise ValueError("birth_confirmation_frames must be a positive integer")


def load_multi_tracking_config(path: Path) -> MultiTrackingConfig:
    """Read association limits without changing the single-fish configuration."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MultiTrackingConfig(**document["multi_tracking"])


@dataclass(frozen=True, slots=True)
class MultiTrackObservation:
    tracked: TrackedDetection
    status: str


@dataclass(slots=True)
class _Track:
    identity: str
    last: Detection2D
    previous: Detection2D | None = None
    hits: int = 1

    def predict(self, time: float) -> tuple[float, float]:
        if self.previous is None:
            return self.last.x_px, self.last.y_px
        dt = self.last.timestamp_s - self.previous.timestamp_s
        horizon = time - self.last.timestamp_s
        return (self.last.x_px + (self.last.x_px - self.previous.x_px) / dt * horizon,
                self.last.y_px + (self.last.y_px - self.previous.y_px) / dt * horizon)


class MultiFishTracker:
    """IDs are view-local segments, not verified individual fish identities.

    Prediction is only an association cost. Exported coordinates always come
    from an observed component; occluded/missing/lost outputs carry NaN.
    """

    def __init__(self, view: View, config: MultiTrackingConfig):
        if view not in ("real", "mirror"):
            raise ValueError("view must be real or mirror")
        self.view, self.config = view, config
        self._tracks: list[_Track] = []
        self._counter = 0
        self._last_frame = -1
        self._last_time = -1.0
        self.last_detection_statuses: list[str] = []

    def update(self, frame_id: int, timestamp_s: float,
               detections: Sequence[Detection2D]) -> list[MultiTrackObservation]:
        """Assign one frame's candidates globally, preserving explicit short gaps."""

        if frame_id <= self._last_frame or not isfinite(timestamp_s) or timestamp_s < 0 or timestamp_s <= self._last_time:
            raise ValueError("frame_id and timestamp_s must increase strictly and be nonnegative")
        for detection in detections:
            if (detection.view, detection.frame_id, detection.timestamp_s) != (self.view, frame_id, timestamp_s):
                raise ValueError("detections must match this view/frame/timestamp")
            if not detection.is_valid or detection.area_px <= 0 or not all(
                isfinite(value) for value in (detection.x_px, detection.y_px)
            ):
                raise ValueError("candidates must be valid finite detections with positive area")
        self._last_frame, self._last_time = frame_id, timestamp_s
        self.last_detection_statuses = ["unassigned"] * len(detections)
        cfg = self.config
        missing = missing_detection(frame_id, timestamp_s, self.view)
        observations = [MultiTrackObservation(TrackedDetection(missing, track.identity), "lost")
                        for track in self._tracks if track.identity and timestamp_s - track.last.timestamp_s > cfg.max_gap_s]
        self._tracks = [track for track in self._tracks if timestamp_s - track.last.timestamp_s <= cfg.max_gap_s]
        confirmed_count = sum(bool(track.identity) for track in self._tracks)
        predictions = [track.predict(timestamp_s) for track in self._tracks]
        merged_indices, occluded_ids = set(), set()
        for index, detection in enumerate(detections):
            near = [track.identity for track, predicted in zip(self._tracks, predictions)
                    if track.identity and hypot(detection.x_px - predicted[0], detection.y_px - predicted[1]) <= cfg.merge_radius_px
                    and detection.area_px >= cfg.merge_area_ratio * track.last.area_px]
            if len(near) >= 2:
                merged_indices.add(index)
                occluded_ids.update(near)
                self.last_detection_statuses[index] = "merged_candidate"
        available = [index for index in range(len(detections)) if index not in merged_indices]
        assignments = {}
        if self._tracks and available:
            distances = np.full((len(self._tracks), len(available)), np.inf)
            for row, (track, predicted) in enumerate(zip(self._tracks, predictions)):
                if track.identity in occluded_ids:
                    continue
                dt = timestamp_s - track.last.timestamp_s
                for column, index in enumerate(available):
                    detection = detections[index]
                    displacement = hypot(detection.x_px - track.last.x_px, detection.y_px - track.last.y_px)
                    error = hypot(detection.x_px - predicted[0], detection.y_px - predicted[1])
                    if displacement <= cfg.max_speed_px_s * dt and error <= cfg.max_prediction_error_px:
                        distances[row, column] = error
            finite = distances[np.isfinite(distances)]
            costs = distances / (1 + float(finite.max()) if finite.size else 1)
            # Prefer retaining confirmed tracks, then maximize remaining feasible matches.
            size = len(self._tracks)
            penalties = np.array([(size + 1) ** 2 if track.identity else size + 1 for track in self._tracks])
            costs = np.concatenate((costs, np.repeat(penalties[:, None], size, axis=1)), axis=1)
            rows, columns = linear_sum_assignment(costs)
            assignments = {int(row): available[int(column)] for row, column in zip(rows, columns)
                           if column < len(available) and isfinite(distances[row, column])}
        used = set(assignments.values())
        retained = []
        for row, track in enumerate(self._tracks):
            if row in assignments:
                index = assignments[row]
                track.hits = track.hits + 1 if detections[index].frame_id == track.last.frame_id + 1 else 1
                track.previous, track.last = track.last, detections[index]
                status = "tracked"
                if not track.identity:
                    if track.hits < cfg.birth_confirmation_frames:
                        self.last_detection_statuses[index] = "tentative"
                        retained.append(track)
                        continue
                    if confirmed_count >= cfg.expected_fish_count:
                        self.last_detection_statuses[index] = "capacity_rejected"
                        continue
                    self._counter += 1
                    track.identity = f"{self.view}_{self._counter:04d}"
                    confirmed_count += 1
                    status = "initialized"
                self.last_detection_statuses[index] = status
                observations.append(MultiTrackObservation(TrackedDetection(track.last, track.identity), status))
                retained.append(track)
            else:
                if track.identity:
                    status = "occluded" if track.identity in occluded_ids else "missing"
                    observations.append(MultiTrackObservation(TrackedDetection(missing, track.identity), status))
                    retained.append(track)
        self._tracks = retained
        # Deterministic births select the largest remaining candidates without truncating raw detections.
        for index in sorted((index for index in available if index not in used), key=lambda index: (
            -detections[index].area_px, detections[index].y_px, detections[index].x_px,
        )):
            if confirmed_count >= cfg.expected_fish_count:
                self.last_detection_statuses[index] = "capacity_rejected"
                continue
            track = _Track("", detections[index])
            self._tracks.append(track)
            if cfg.birth_confirmation_frames == 1:
                self._counter += 1
                track.identity = f"{self.view}_{self._counter:04d}"
                confirmed_count += 1
                self.last_detection_statuses[index] = "initialized"
                observations.append(MultiTrackObservation(TrackedDetection(track.last, track.identity), "initialized"))
            else:
                self.last_detection_statuses[index] = "tentative"
        return observations
