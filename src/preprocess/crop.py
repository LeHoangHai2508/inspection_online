from __future__ import annotations

from io import BytesIO
from pathlib import Path

from src.domain.enums import InspectionSide
from src.domain.models import CaptureInput
from src.utils.config_loader import load_yaml_config

_DEFAULT_CAMERA_CONFIG = {
    "side1": {"search_window": {"x": 60, "y": 40, "w": 620, "h": 980}},
    "side2": {"search_window": {"x": 70, "y": 50, "w": 620, "h": 980}},
}


def crop_search_window(capture: CaptureInput, side: InspectionSide) -> CaptureInput:
    """
    Cắt vùng tìm kiếm (search window) rộng hơn ROI cuối cùng.

    Mục đích:
    - Không cắt thẳng vào ROI cuối như luồng cũ.
    - Giữ đủ margin để localize_label tự tìm tem bên trong vùng này.
    - Cho phép tem bị lệch nhẹ hoặc nghiêng nhẹ nhưng vẫn nằm trong vùng tìm.

    Text fixtures (unit test) pass-through không thay đổi.
    """
    if capture.media_type.startswith("text/"):
        return capture

    if not capture.media_type.startswith("image/"):
        return capture

    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return capture

    config = load_yaml_config("configs/camera.yaml", default=_DEFAULT_CAMERA_CONFIG)
    window = config.get(side.value, {}).get(
        "search_window",
        _DEFAULT_CAMERA_CONFIG[side.value]["search_window"],
    )

    image = Image.open(BytesIO(capture.content))
    x = int(window["x"])
    y = int(window["y"])
    w = int(window["w"])
    h = int(window["h"])

    # Giới hạn trong kích thước ảnh thật để tránh out-of-bounds
    img_w, img_h = image.size
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = min(w, img_w - x)
    h = min(h, img_h - y)

    cropped = image.crop((x, y, x + w, y + h))
    output = BytesIO()
    cropped.save(output, format=image.format or "PNG")

    return CaptureInput(
        filename=_with_suffix(capture.filename, "_search"),
        content=output.getvalue(),
        media_type=capture.media_type,
        camera_id=capture.camera_id,
    )


def _with_suffix(filename: str, suffix: str) -> str:
    path = Path(filename)
    return f"{path.stem}{suffix}{path.suffix or '.png'}"
