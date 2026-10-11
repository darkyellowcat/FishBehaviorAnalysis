"""Paper ideal pixel-coordinate model; not a calibrated metric reconstruction."""

from dataclasses import dataclass
from math import isfinite, nan, radians, tan
from pathlib import Path
from typing import Literal

import yaml

from fish3d.interfaces import TrackedDetection
from fish3d.schemas import TrajectoryPoint

GEOMETRY_VERSION = "paper_ideal_full_frame_pixel_v1"


@dataclass(frozen=True, slots=True)
class GeometryConfig:
    mirror_angle_deg: float
    mirror_intersection_x_px: float
    image_origin_px: tuple[float, float]
    coordinate_unit: str
    coordinate_frame: str

    def __post_init__(self) -> None:
        if not isfinite(self.mirror_angle_deg) or not 0 < self.mirror_angle_deg < 90:
            raise ValueError("mirror_angle_deg must be finite and strictly between 0 and 90")
        if not isfinite(self.mirror_intersection_x_px):
            raise ValueError("mirror_intersection_x_px must be finite")
        if len(self.image_origin_px) != 2 or not all(isfinite(value) for value in self.image_origin_px):
            raise ValueError("image_origin_px requires two finite coordinates")
        if self.coordinate_unit != "model_px" or self.coordinate_frame != "paper_ideal_cartesian":
            raise ValueError("paper ideal geometry requires model_px and paper_ideal_cartesian; no physical units")


def load_geometry_config(path: Path) -> GeometryConfig:
    """Load angle, full-frame mirror reference, origin and explicit model units."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    settings = dict(document["geometry"])
    settings["image_origin_px"] = tuple(settings["image_origin_px"])
    return GeometryConfig(**settings)


def paired_track_id(real: TrackedDetection, mirror: TrackedDetection) -> str:
    """Name a pair of 2D segments; this is an assumed correspondence identity."""

    if real.fish_id and mirror.fish_id:
        return f"{real.fish_id}__{mirror.fish_id}"
    return "unassigned"


class PaperIdealReconstructor:
    """Implement X=x, Y=y, Z=(a-x')tan(alpha) with a declared image origin.

    Both views use processed full-frame pixels. a is the full-frame mirror
    intersection coordinate, independent of the ROI boundary configuration.
    """

    def __init__(
        self, config: GeometryConfig, data_source: Literal["synthetic", "experimental"],
    ) -> None:
        if data_source not in ("synthetic", "experimental"):
            raise ValueError("data_source must be synthetic or experimental")
        self.config = config
        self.data_source = data_source
        self._slope = tan(radians(config.mirror_angle_deg))

    def invalid_point(self, frame_id: int, timestamp_s: float, fish_id: str) -> TrajectoryPoint:
        """Retain a frame as an entirely invalid 3D observation."""

        return TrajectoryPoint(
            frame_id, timestamp_s, fish_id, nan, nan, nan,
            self.config.coordinate_unit, False, self.config.coordinate_frame, self.data_source,
        )

    def reconstruct(self, real: TrackedDetection, mirror: TrackedDetection) -> TrajectoryPoint:
        """Convert synchronized centroids; any missing view yields all-NaN XYZ."""

        first, second = real.detection, mirror.detection
        if first.view != "real" or second.view != "mirror":
            raise ValueError("arguments must be ordered real, mirror")
        if first.frame_id != second.frame_id or first.timestamp_s != second.timestamp_s:
            raise ValueError("reconstruction requires the same frame_id and timestamp_s")
        identity = paired_track_id(real, mirror)
        if not (first.is_valid and second.is_valid):
            return self.invalid_point(first.frame_id, first.timestamp_s, identity)
        if not (real.fish_id and mirror.fish_id):
            raise ValueError("valid reconstruction requires two track IDs")
        if not all(isfinite(value) for value in (first.x_px, first.y_px, second.x_px, second.y_px)):
            raise ValueError("valid reconstruction requires finite pixel coordinates")
        origin_x, origin_y = self.config.image_origin_px
        return TrajectoryPoint(
            first.frame_id, first.timestamp_s, identity,
            first.x_px - origin_x, first.y_px - origin_y,
            (self.config.mirror_intersection_x_px - second.x_px) * self._slope,
            self.config.coordinate_unit, True, self.config.coordinate_frame, self.data_source,
        )

    def project(self, point: TrajectoryPoint) -> tuple[tuple[float, float], tuple[float, float]]:
        """Invert this ideal model for synthetic verification, returning full pixels.

        This is not pinhole camera rendering or a refraction/mirror ray model.
        """

        if not point.is_valid:
            raise ValueError("cannot project an invalid point")
        if point.coordinate_unit != self.config.coordinate_unit or point.coordinate_frame != self.config.coordinate_frame:
            raise ValueError("point coordinate unit/frame does not match the ideal model")
        origin_x, origin_y = self.config.image_origin_px
        real = (point.X + origin_x, point.Y + origin_y)
        mirror = (self.config.mirror_intersection_x_px - point.Z / self._slope, real[1])
        return real, mirror
