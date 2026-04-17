from __future__ import annotations

from io import BytesIO

from src.domain.models import CaptureInput


def normalize_capture(capture: CaptureInput) -> CaptureInput:
    if capture.media_type.startswith("text/"):
        return capture

    if not capture.media_type.startswith("image/"):
        return capture

    try:
        from PIL import Image, ImageOps  # type: ignore
    except ImportError:
        return capture

    image = Image.open(BytesIO(capture.content))
    normalized = ImageOps.autocontrast(image)
    output = BytesIO()
    normalized.save(output, format=image.format or "PNG")
    return CaptureInput(
        filename=capture.filename,
        content=output.getvalue(),
        media_type=capture.media_type,
        camera_id=capture.camera_id,
    )
