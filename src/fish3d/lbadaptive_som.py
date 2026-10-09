"""LBAdaptiveSOM baseline from the fish paper, equations (2)--(5)."""

import json
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path

import numpy as np
import yaml

from fish3d.interfaces import ForegroundMask, ViewFrame

ALGORITHM_VERSION = "paper2015_hsv_squared_v1"


@dataclass(frozen=True, slots=True)
class SOMConfig:
    mapping_size: int
    learning_frames: int
    epsilon_learning: float
    epsilon_online: float
    learning_rate: float
    gaussian_sigma: float
    shadow_gamma: float
    shadow_beta: float
    shadow_saturation_tolerance: float
    shadow_hue_tolerance_deg: float

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_size, int) or self.mapping_size < 1 or self.mapping_size % 2 == 0:
            raise ValueError("mapping_size must be a positive odd integer")
        if not isinstance(self.learning_frames, int) or self.learning_frames < 1:
            raise ValueError("learning_frames must include at least the initialization frame")
        numeric = (
            self.epsilon_learning, self.epsilon_online, self.learning_rate,
            self.gaussian_sigma, self.shadow_gamma, self.shadow_beta,
            self.shadow_saturation_tolerance, self.shadow_hue_tolerance_deg,
        )
        if not all(isfinite(value) for value in numeric):
            raise ValueError("SOM parameters must be finite")
        if not 0 < self.epsilon_online <= self.epsilon_learning:
            raise ValueError("thresholds require 0 < epsilon_online <= epsilon_learning")
        if not 0 < self.learning_rate <= 1 or self.gaussian_sigma <= 0:
            raise ValueError("learning_rate must be in (0, 1] and gaussian_sigma positive")
        if not 0 <= self.shadow_gamma <= self.shadow_beta <= 1:
            raise ValueError("shadow brightness ratios must satisfy 0 <= gamma <= beta <= 1")
        if not 0 <= self.shadow_saturation_tolerance <= 1 or not 0 <= self.shadow_hue_tolerance_deg <= 360:
            raise ValueError("shadow tolerances are outside their HSV ranges")


def load_som_config(path: Path) -> SOMConfig:
    """Read the som section alongside the existing S2 video configuration."""

    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("som"), dict):
        raise ValueError("configuration requires a som mapping")
    return SOMConfig(**document["som"])


def normalize_opencv_hsv(image: np.ndarray) -> np.ndarray:
    """Convert uint8 OpenCV HSV to floating (H degrees, S/V in 0..1)."""

    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("SOM input must be an H x W x 3 uint8 HSV array")
    if image.shape[0] == 0 or image.shape[1] == 0 or np.any(image[..., 0] > 179):
        raise ValueError("SOM input requires nonempty OpenCV HSV with H in 0..179")
    result = image.astype(np.float64)
    result[..., 0] *= 2.0
    result[..., 1:] /= 255.0
    return result


def hsv_distance_squared(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """Equation (2): squared cylindrical HSV distance, with H in degrees."""

    first_radius = first[..., 1] * first[..., 2]
    second_radius = second[..., 1] * second[..., 2]
    angle = np.deg2rad(first[..., 0] - second[..., 0])
    # Algebraic form of ||(VS cos H, VS sin H, V)_1 - (...)_2||_2^2.
    distance = (
        (first_radius - second_radius) ** 2
        + 2 * first_radius * second_radius * (1 - np.cos(angle))
        + (first[..., 2] - second[..., 2]) ** 2
    )
    return distance


class LBAdaptiveSOM:
    """One view's spatial SOM; each input pixel owns an n x n model block.

    Updates use a Gaussian neighborhood in the full enlarged model lattice,
    including neighboring input pixels' blocks. Pixels are processed in a fixed
    row-major order. HSV weights use equation (5)'s linear update literally.
    """

    def __init__(self, config: SOMConfig) -> None:
        self.config = config
        self.weights_hsv: np.ndarray | None = None
        self.processed_frames = 0
        self.last_stats: dict = {}
        self._geometry: tuple | None = None
        self._last_frame_id = -1
        self._last_timestamp = -1.0
        radius = config.mapping_size // 2
        dy, dx = np.mgrid[-radius:radius + 1, -radius:radius + 1]
        self._gain = config.learning_rate * np.exp(
            -(dy * dy + dx * dx) / (2 * config.gaussian_sigma ** 2)
        )

    def _update(self, row: int, column: int, pixel: np.ndarray) -> None:
        """Update a clipped neighborhood without wrapping at the model edges."""

        radius = self.config.mapping_size // 2
        height, width = self.weights_hsv.shape[:2]
        top, bottom = max(0, row - radius), min(height, row + radius + 1)
        left, right = max(0, column - radius), min(width, column + radius + 1)
        gain = self._gain[
            top - row + radius:bottom - row + radius,
            left - column + radius:right - column + radius,
        ][..., None]
        neighborhood = self.weights_hsv[top:bottom, left:right]
        neighborhood += gain * (pixel - neighborhood)

    def _is_shadow(self, pixel: np.ndarray, reference: np.ndarray) -> bool:
        # A black reference cannot define a brightness ratio.
        if reference[2] == 0:
            return False
        ratio = pixel[2] / reference[2]
        return bool(
            self.config.shadow_gamma <= ratio <= self.config.shadow_beta
            and pixel[1] - reference[1] <= self.config.shadow_saturation_tolerance
            and abs(pixel[0] - reference[0]) <= self.config.shadow_hue_tolerance_deg
        )

    def segment(self, view_frame: ViewFrame) -> ForegroundMask:
        """Return an ROI-local 0/255 foreground mask and retain model state."""

        image = normalize_opencv_hsv(view_frame.image)
        if view_frame.frame_id <= self._last_frame_id or not isfinite(view_frame.timestamp_s) or view_frame.timestamp_s <= self._last_timestamp:
            raise ValueError("SOM frames and timestamps must increase strictly")
        geometry = (view_frame.view, view_frame.roi_x, view_frame.roi_y, image.shape)
        if self._geometry is not None and geometry != self._geometry:
            raise ValueError("one SOM instance must keep the same view and ROI geometry")
        n = self.config.mapping_size
        threshold = self.config.epsilon_learning if self.processed_frames < self.config.learning_frames else self.config.epsilon_online
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        foreground_count = shadow_count = update_count = 0
        if self.weights_hsv is None:
            self.weights_hsv = np.repeat(np.repeat(image, n, axis=0), n, axis=1)
            self._geometry = geometry
            phase = "initialization"
        else:
            phase = "learning" if self.processed_frames < self.config.learning_frames else "online"
            for y in range(image.shape[0]):
                for x in range(image.shape[1]):
                    pixel = image[y, x]
                    block = self.weights_hsv[y * n:(y + 1) * n, x * n:(x + 1) * n]
                    distances = hsv_distance_squared(pixel, block)
                    winner = int(np.argmin(distances))
                    winner_y, winner_x = divmod(winner, n)
                    if distances[winner_y, winner_x] <= threshold:
                        self._update(y * n + winner_y, x * n + winner_x, pixel)
                        update_count += 1
                    elif self._is_shadow(pixel, block[winner_y, winner_x]):
                        shadow_count += 1
                    else:
                        mask[y, x] = 255
                        foreground_count += 1
        self.last_stats = {
            "phase": phase, "threshold_squared": threshold,
            "foreground_pixels": foreground_count, "shadow_pixels": shadow_count,
            "background_updates": update_count,
        }
        self.processed_frames += 1
        self._last_frame_id = view_frame.frame_id
        self._last_timestamp = view_frame.timestamp_s
        return ForegroundMask(
            view_frame.frame_id, view_frame.timestamp_s, view_frame.view,
            mask, view_frame.roi_x, view_frame.roi_y,
        )

    def save_model(self, path: Path, *, data_source: str) -> None:
        """Save the full lattice plus its HSV scale and processing metadata."""

        if self.weights_hsv is None:
            raise ValueError("cannot save an uninitialized SOM")
        if data_source not in ("synthetic", "experimental"):
            raise ValueError("model data_source must be synthetic or experimental")
        metadata = {
            "algorithm_version": ALGORITHM_VERSION,
            "data_source": data_source,
            "config": asdict(self.config), "processed_frames": self.processed_frames,
            "view": self._geometry[0], "roi_x": self._geometry[1], "roi_y": self._geometry[2],
            "last_frame_id": self._last_frame_id, "last_timestamp_s": self._last_timestamp,
            "weight_scale": "H degrees; S/V 0..1",
        }
        np.savez_compressed(path, weights_hsv=self.weights_hsv, metadata=json.dumps(metadata))

