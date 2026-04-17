from __future__ import annotations

from io import BytesIO

from src.domain.models import BoundingBox, CaptureInput
from src.preprocess.types import LocalizedLabel


def localize_label(capture: CaptureInput) -> LocalizedLabel:
    """
    Tìm vùng tem trong search window bằng rule-based contour.

    Đây là Phase 1 — ưu tiên đơn giản và dễ debug.
    - Không cần dataset training.
    - Nếu không tìm thấy contour hợp lý → trả bbox=None (pipeline đánh dấu UNCERTAIN).

    Luồng:
        search window → grayscale → blur → Canny edges → contours
        → chọn contour lớn nhất hợp lệ → bbox + 4 corners.
    """
    # Text fixtures dùng trong unit test — pass-through
    if capture.media_type.startswith("text/"):
        return LocalizedLabel(
            capture=capture,
            bbox=None,
            corners=[],
            confidence=0.0,
            method="text-fixture",
        )

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        return LocalizedLabel(
            capture=capture,
            bbox=None,
            corners=[],
            confidence=0.0,
            method="backend-missing",
        )

    image = Image.open(BytesIO(capture.content)).convert("RGB")
    image_np = np.array(image)

    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_bbox: BoundingBox | None = None
    best_area = 0
    best_corners: list[tuple[int, int]] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 3000:
            # Bỏ qua contour quá nhỏ (nhiễu, vết bẩn nhỏ)
            continue

        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect).astype(int)

        x, y, w, h = cv2.boundingRect(box)
        if w <= 0 or h <= 0:
            continue

        if area > best_area:
            best_area = area
            best_bbox = BoundingBox(x1=x, y1=y, x2=x + w, y2=y + h)
            best_corners = [(int(px), int(py)) for px, py in box]

    if best_bbox is None:
        return LocalizedLabel(
            capture=capture,
            bbox=None,
            corners=[],
            confidence=0.0,
            method="rule-based-contour",
        )

    # confidence thô: diện tích tìm được / diện tích tham chiếu 50k px
    confidence = round(min(1.0, best_area / 50_000.0), 3)

    return LocalizedLabel(
        capture=capture,
        bbox=best_bbox,
        corners=best_corners,
        confidence=confidence,
        method="rule-based-contour",
    )
