from __future__ import annotations

from dataclasses import dataclass
from typing import List

import cv2
import numpy as np

from src.domain.models import BoundingBox, CaptureInput


@dataclass(frozen=True)
class SymbolRegion:
    bbox: BoundingBox
    image: np.ndarray


def detect_symbol_regions(capture: CaptureInput) -> List[SymbolRegion]:
    arr = np.frombuffer(capture.content, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []

    # threshold để lấy nét icon
    _, thresh = cv2.threshold(
        image,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    regions: List[SymbolRegion] = []
    h, w = image.shape[:2]

    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)

        # lọc nhiễu nhỏ
        if bw < 12 or bh < 12:
            continue

        # bỏ contour quá to
        if bw > w * 0.5 or bh > h * 0.5:
            continue

        # icon care symbol thường khá vuông / chữ nhật nhỏ
        area = bw * bh
        if area < 200:
            continue

        crop = image[y:y+bh, x:x+bw]
        regions.append(
            SymbolRegion(
                bbox=BoundingBox(x, y, x + bw, y + bh),
                image=crop,
            )
        )

    # sort trái -> phải, trên -> dưới
    regions.sort(key=lambda r: (r.bbox.y1, r.bbox.x1))
    return regions
