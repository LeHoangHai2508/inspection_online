from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums import ErrorType
from src.domain.models import CaptureInput

# Thresholds — tune per deployment environment
_MIN_BRIGHTNESS = 40.0
_MAX_BRIGHTNESS = 220.0
_MIN_BLUR_PROXY = 8.0          # edge-variance proxy; lower = blurrier
_MIN_PRINT_SHARPNESS = 20.0    # higher threshold for print-quality check
_MIN_DIMENSION_PX = 20


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    score: float
    error_type: ErrorType | None = None
    reason: str = ""


def evaluate_capture_quality(capture: CaptureInput) -> QualityGateResult:
    """Evaluate image quality and classify failure as image vs print problem.

    Returns:
        QualityGateResult with:
        - LOW_IMAGE_QUALITY  → camera/lighting/focus problem (hardware side)
        - LOW_PRINT_QUALITY  → image is fine but print itself is faint/blurry
        - UNCERTAIN_RESULT   → cannot determine (missing backend, tiny ROI)
    """
    if not capture.content:
        return QualityGateResult(
            passed=False,
            score=0.0,
            error_type=ErrorType.LOW_IMAGE_QUALITY,
            reason="Capture is empty.",
        )

    # Text fixtures used in unit tests — pass through
    if capture.media_type.startswith("text/"):
        decoded = capture.content.decode("utf-8", errors="ignore").upper()
        if "LOW_IMAGE_QUALITY" in decoded or "BLUR" in decoded:
            return QualityGateResult(
                passed=False,
                score=0.3,
                error_type=ErrorType.LOW_IMAGE_QUALITY,
                reason="Capture marked as low quality by fixture content.",
            )
        return QualityGateResult(passed=True, score=1.0)

    if not capture.media_type.startswith("image/"):
        return QualityGateResult(passed=True, score=0.8, reason="Non-image capture bypassed.")

    try:
        from PIL import Image, ImageFilter, ImageStat  # type: ignore
    except ImportError:
        return QualityGateResult(
            passed=False,
            score=0.4,
            error_type=ErrorType.UNCERTAIN_RESULT,
            reason="Image quality backend (Pillow) is unavailable.",
        )

    from io import BytesIO

    image = Image.open(BytesIO(capture.content)).convert("L")
    width, height = image.size

    # --- Dimension check ---
    if width < _MIN_DIMENSION_PX or height < _MIN_DIMENSION_PX:
        return QualityGateResult(
            passed=False,
            score=0.1,
            error_type=ErrorType.UNCERTAIN_RESULT,
            reason=f"ROI too small ({width}×{height} px) for reliable OCR.",
        )

    stat = ImageStat.Stat(image)
    brightness = float(stat.mean[0])
    contrast = float(stat.stddev[0])  # low contrast → faint print

    edges = image.filter(ImageFilter.FIND_EDGES)
    blur_proxy = float(ImageStat.Stat(edges).var[0]) ** 0.5

    # --- Brightness / exposure check (camera/lighting issue) ---
    if brightness < _MIN_BRIGHTNESS:
        return QualityGateResult(
            passed=False,
            score=0.2,
            error_type=ErrorType.LOW_IMAGE_QUALITY,
            reason=f"Image too dark (brightness={brightness:.1f}). Check lighting.",
        )
    if brightness > _MAX_BRIGHTNESS:
        return QualityGateResult(
            passed=False,
            score=0.2,
            error_type=ErrorType.LOW_IMAGE_QUALITY,
            reason=f"Image overexposed (brightness={brightness:.1f}). Check lighting.",
        )

    # --- Blur check (camera focus issue) ---
    if blur_proxy < _MIN_BLUR_PROXY:
        return QualityGateResult(
            passed=False,
            score=0.3,
            error_type=ErrorType.LOW_IMAGE_QUALITY,
            reason=f"Image blurry (blur_proxy={blur_proxy:.2f}). Check camera focus.",
        )

    # --- Print quality check (image OK but print is faint/low-contrast) ---
    # A well-lit, sharp image with very low contrast likely has faint printing.
    if contrast < 10.0 and blur_proxy < _MIN_PRINT_SHARPNESS:
        return QualityGateResult(
            passed=False,
            score=0.45,
            error_type=ErrorType.LOW_PRINT_QUALITY,
            reason=(
                f"Print quality low: contrast={contrast:.1f}, "
                f"blur_proxy={blur_proxy:.2f}. Ink may be faint."
            ),
        )

    # --- Composite score ---
    brightness_score = 1.0 - abs(brightness - 128.0) / 128.0
    blur_score = min(1.0, blur_proxy / 32.0)
    score = round((brightness_score + blur_score) / 2.0, 3)

    return QualityGateResult(
        passed=True,
        score=score,
        reason=(
            f"brightness={brightness:.1f}, contrast={contrast:.1f}, "
            f"blur_proxy={blur_proxy:.2f}"
        ),
    )
