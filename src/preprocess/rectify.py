from __future__ import annotations

from io import BytesIO

from src.domain.models import CaptureInput
from src.preprocess.types import LocalizedLabel, RectifiedCapture


def rectify_label(localized: LocalizedLabel) -> RectifiedCapture:
    """
    Nắn thẳng ảnh tem từ kết quả localization.

    Chiến lược (theo thứ tự ưu tiên):
    1. Có đủ 4 corners → perspective warp (tốt nhất).
    2. Chỉ có bbox → crop theo bbox (chấp nhận được).
    3. Không có gì (bbox=None) → trả nguyên ảnh, alignment_applied=False.

    Output luôn là PNG để downstream nhất quán.
    """
    if localized.bbox is None:
        return RectifiedCapture(
            capture=localized.capture,
            alignment_applied=False,
            method="no-localization",
        )

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        return RectifiedCapture(
            capture=localized.capture,
            alignment_applied=False,
            method="backend-missing",
        )

    image = Image.open(BytesIO(localized.capture.content)).convert("RGB")
    image_np = np.array(image)

    if len(localized.corners) == 4:
        pts = np.array(localized.corners, dtype="float32")
        pts = _order_points(pts)

        width_a = _dist(pts[2], pts[3])
        width_b = _dist(pts[1], pts[0])
        max_width = max(1, int(max(width_a, width_b)))

        height_a = _dist(pts[1], pts[2])
        height_b = _dist(pts[0], pts[3])
        max_height = max(1, int(max(height_a, height_b)))

        dst = np.array(
            [
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1],
            ],
            dtype="float32",
        )

        matrix = cv2.getPerspectiveTransform(pts, dst)
        warped = cv2.warpPerspective(image_np, matrix, (max_width, max_height))
        final_image = Image.fromarray(warped)
        method = "perspective-warp"
    else:
        bbox = localized.bbox
        final_image = image.crop((bbox.x1, bbox.y1, bbox.x2, bbox.y2))
        method = "bbox-crop"

    output = BytesIO()
    final_image.save(output, format="PNG")

    return RectifiedCapture(
        capture=CaptureInput(
            filename=localized.capture.filename,
            content=output.getvalue(),
            media_type="image/png",
            camera_id=localized.capture.camera_id,
        ),
        alignment_applied=True,
        method=method,
    )


def _dist(a: "np.ndarray", b: "np.ndarray") -> float:
    return float(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5)


def _order_points(points: "np.ndarray") -> "np.ndarray":
    """
    Sắp xếp 4 điểm thành thứ tự: TL, TR, BR, BL.
    Dùng tổng và hiệu tọa độ làm key.
    """
    import numpy as np  # type: ignore

    rect = np.zeros((4, 2), dtype="float32")
    s = points.sum(axis=1)
    rect[0] = points[np.argmin(s)]   # TL: tổng nhỏ nhất
    rect[2] = points[np.argmax(s)]   # BR: tổng lớn nhất

    diff = np.diff(points, axis=1)
    rect[1] = points[np.argmin(diff)]  # TR: hiệu nhỏ nhất
    rect[3] = points[np.argmax(diff)]  # BL: hiệu lớn nhất
    return rect
