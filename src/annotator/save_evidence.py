from __future__ import annotations

from io import BytesIO
from pathlib import Path

from src.domain.models import CaptureInput, ComparisonError
from src.utils.json_utils import write_json
from src.utils.paths import ANNOTATION_STORAGE, make_side_folder


def save_evidence_artifacts(
    scan_job_id: str,
    side_name: str,
    camera_id: str,
    capture: CaptureInput,
    errors: list[ComparisonError],
) -> dict[str, str]:
    """
    Lưu bundle evidence cho một camera mỗi lần inspection:

    1. aligned/raw image — ảnh đã qua search window + localize + rectify + normalize
    2. annotated image   — ảnh có vẽ bbox đỏ tại vị trí các lỗi
    3. summary JSON      — danh sách lỗi theo field

    Trả về dict với 3 key:
        "aligned_image"   → đường dẫn tuyệt đối file ảnh đã xử lý
        "annotated_image" → đường dẫn tuyệt đối file ảnh annotated
        "summary_json"    → đường dẫn tuyệt đối file JSON
    """
    side_folder = make_side_folder(ANNOTATION_STORAGE, scan_job_id, side_name)

    # 1) Lưu ảnh đã xử lý (aligned)
    raw_path = side_folder / _build_filename(camera_id, "aligned", capture)
    raw_path.write_bytes(capture.content)

    # 2) Lưu JSON summary
    summary_path = side_folder / f"{camera_id}_summary.json"
    write_json(
        summary_path,
        [
            {
                "field_name": error.field_name,
                "error_type": error.error_type.value,
                "expected_value": error.expected_value,
                "actual_value": error.actual_value,
                "severity": error.severity.value,
                "message": error.message,
                "camera_source": error.camera_source,
                "bbox": (
                    {
                        "x1": error.bbox.x1,
                        "y1": error.bbox.y1,
                        "x2": error.bbox.x2,
                        "y2": error.bbox.y2,
                    }
                    if error.bbox
                    else None
                ),
            }
            for error in errors
        ],
    )

    # 3) Lưu ảnh annotated (vẽ bbox đỏ tại vị trí lỗi)
    annotated_path = side_folder / f"{camera_id}_annotated.png"
    _draw_error_boxes(capture, errors, annotated_path)

    return {
        "aligned_image": str(raw_path),
        "annotated_image": str(annotated_path),
        "summary_json": str(summary_path),
    }


# ── Backward-compat wrapper (giữ cho code ngoài không lỗi ngay) ────────────
def save_annotation_summary(
    scan_job_id: str,
    side_name: str,
    camera_id: str,
    errors: list[ComparisonError],
) -> str:
    """
    Deprecated: dùng save_evidence_artifacts thay thế.
    Wrapper này giữ để tránh phá code cũ chưa kịp migrate.
    """
    from src.utils.paths import ANNOTATION_STORAGE

    path = ANNOTATION_STORAGE / scan_job_id / f"{side_name}_{camera_id}.json"
    write_json(
        path,
        [
            {
                "field_name": error.field_name,
                "error_type": error.error_type.value,
                "expected_value": error.expected_value,
                "actual_value": error.actual_value,
                "severity": error.severity.value,
            }
            for error in errors
        ],
    )
    return str(path)


# ── Internal helpers ───────────────────────────────────────────────────────

def _build_filename(camera_id: str, label: str, capture: CaptureInput) -> str:
    suffix = Path(capture.filename).suffix or ".bin"
    return f"{camera_id}_{label}{suffix}"


def _draw_error_boxes(
    capture: CaptureInput,
    errors: list[ComparisonError],
    output_path: Path,
) -> None:
    """
    Nếu là ảnh thật → vẽ bbox đỏ lên ảnh rồi lưu PNG.
    Nếu không phải ảnh (text fixture, dữ liệu binary khác) → copy raw bytes.
    Nếu Pillow chưa cài → copy raw bytes.
    """
    if not capture.media_type.startswith("image/"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(capture.content)
        return

    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(capture.content)
        return

    image = Image.open(BytesIO(capture.content)).convert("RGB")
    draw = ImageDraw.Draw(image)

    for error in errors:
        if error.bbox is None:
            continue
        draw.rectangle(
            [(error.bbox.x1, error.bbox.y1), (error.bbox.x2, error.bbox.y2)],
            outline="red",
            width=3,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
