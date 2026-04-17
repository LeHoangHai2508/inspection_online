from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import BoundingBox, CaptureInput


@dataclass(frozen=True)
class LocalizedLabel:
    """
    Kết quả tìm vùng tem trong search window.

    Trách nhiệm duy nhất: mô tả vị trí tem tìm được.
    Không chứa kết quả OCR hay decision.
    """

    capture: CaptureInput
    """Search-window capture đã dùng để tìm."""

    bbox: BoundingBox | None
    """Bounding box (x1,y1)-(x2,y2) trong hệ tọa độ search window."""

    corners: list[tuple[int, int]]
    """4 góc theo thứ tự TL, TR, BR, BL (nếu có). Dùng cho perspective warp."""

    confidence: float
    """Độ tin cậy [0.0, 1.0]. 0.0 = không tìm thấy tem."""

    method: str
    """Nhãn debug: phương pháp đã dùng (rule-based-contour, text-fixture …)."""


@dataclass(frozen=True)
class RectifiedCapture:
    """
    Ảnh tem sau khi đã nắn thẳng hoặc crop về ROI cuối.

    Trách nhiệm duy nhất: mang ảnh đã được chuẩn bị sẵn để OCR.
    """

    capture: CaptureInput
    """CaptureInput chứa ảnh đã được nắn/crop."""

    alignment_applied: bool
    """True nếu đã warp hay crop thành công."""

    method: str
    """Nhãn debug: perspective-warp / bbox-crop / no-localization / backend-missing."""
