"""Single-fish pixel centroids with explicit engineering mask cleanup."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml

from fish3d.interfaces import Detection2D, ForegroundMask


@dataclass(frozen=True, slots=True)
class CentroidConfig:
    min_area_px: int
    max_area_px: int
    opening_kernel: int
    closing_kernel: int
    connectivity: int

    def __post_init__(self) -> None:
        if self.min_area_px < 1 or self.max_area_px < self.min_area_px:
            raise ValueError("area limits must be positive and ordered")
        for size in (self.opening_kernel, self.closing_kernel):
            if size != 0 and (size < 3 or size % 2 == 0):
                raise ValueError("morphology kernels must be 0 (disabled) or odd and at least 3")
        if self.connectivity not in (4, 8):
            raise ValueError("connectivity must be 4 or 8")


def load_centroid_config(path: Path) -> CentroidConfig:
    """Read the centroid section of the shared video configuration."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CentroidConfig(**document["centroid"])


class ConnectedComponentCentroidExtractor:
    """Select the largest area-qualified component and average its pixels.

    Cleanup and component selection are engineering additions to the paper.
    Coordinates refer to the processed full frame, including the ROI offset.
    """

    def __init__(self, config: CentroidConfig) -> None:
        self.config = config
        self.last_cleaned_mask: np.ndarray | None = None
        self.last_candidate_count = 0

    def extract(self, mask: ForegroundMask) -> Detection2D | None:
        """Return None when no component satisfies the configured area limits."""

        image = mask.mask
        if image.dtype != np.uint8 or image.ndim != 2 or image.size == 0:
            raise ValueError("foreground mask must be a nonempty 2D uint8 array")
        if not np.all((image == 0) | (image == 255)):
            raise ValueError("foreground mask must contain only 0/255")
        cleaned = image.copy()
        for operation, size in (
            (cv2.MORPH_OPEN, self.config.opening_kernel),
            (cv2.MORPH_CLOSE, self.config.closing_kernel),
        ):
            if size:
                cleaned = cv2.morphologyEx(
                    cleaned, operation, np.ones((size, size), dtype=np.uint8),
                    borderType=cv2.BORDER_CONSTANT, borderValue=0,
                )
        self.last_cleaned_mask = cleaned
        count, _, stats, centers = cv2.connectedComponentsWithStats(
            cleaned, connectivity=self.config.connectivity,
        )
        candidates = [
            label for label in range(1, count)
            if self.config.min_area_px <= stats[label, cv2.CC_STAT_AREA] <= self.config.max_area_px
        ]
        self.last_candidate_count = len(candidates)
        if not candidates:
            return None
        # Equal areas are resolved by centroid y then x, independent of label IDs.
        selected = min(candidates, key=lambda label: (
            -int(stats[label, cv2.CC_STAT_AREA]), centers[label, 1], centers[label, 0],
        ))
        return Detection2D(
            mask.frame_id, mask.timestamp_s, mask.view,
            float(centers[selected, 0] + mask.roi_x),
            float(centers[selected, 1] + mask.roi_y),
            int(stats[selected, cv2.CC_STAT_AREA]), True,
        )
