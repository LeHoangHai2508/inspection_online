"""
Module lưu trữ bằng chứng (evidence) cho quá trình kiểm tra nhãn mác.

Module này chịu trách nhiệm lưu lại toàn bộ artifacts cần thiết để:
1. Audit trail: Truy vết lại quá trình kiểm tra
2. Debug: Phân tích lỗi khi có sự cố
3. Training data: Thu thập dữ liệu để cải thiện model
4. Compliance: Đáp ứng yêu cầu lưu trữ chứng từ

Cấu trúc thư mục evidence:
    storage/annotations/
        {scan_job_id}/
            {side_name}/
                {camera_id}_aligned.jpg      # Ảnh đã qua xử lý (rectify, normalize)
                {camera_id}_annotated.png    # Ảnh đã vẽ bbox lỗi màu đỏ
                {camera_id}_summary.json     # Danh sách lỗi chi tiết

Luồng xử lý:
    1. Nhận ảnh đã qua preprocess (aligned)
    2. Nhận danh sách lỗi phát hiện được
    3. Lưu ảnh aligned
    4. Vẽ bbox đỏ lên vị trí lỗi → lưu ảnh annotated
    5. Lưu summary JSON với thông tin lỗi chi tiết
"""
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
    Lưu bundle evidence đầy đủ cho một camera trong mỗi lần inspection.
    
    Function này là điểm trung tâm để lưu trữ toàn bộ artifacts cần thiết
    cho việc audit, debug, và training. Mỗi lần gọi sẽ tạo ra 3 files:
    
    1. Aligned image: Ảnh đã qua pipeline preprocess đầy đủ
       - Search window: Tìm vùng chứa nhãn mác
       - Localize: Xác định chính xác vị trí nhãn
       - Rectify: Chỉnh góc nghiêng
       - Normalize: Chuẩn hóa brightness/contrast
       
    2. Annotated image: Ảnh có vẽ bbox màu đỏ tại vị trí các lỗi
       - Giúp visualize nhanh các lỗi phát hiện được
       - Dùng cho QA review và debug
       
    3. Summary JSON: Metadata chi tiết về các lỗi
       - field_name: Tên trường bị lỗi
       - error_type: Loại lỗi (TEXT_MISMATCH, SYMBOL_MISSING, etc.)
       - expected vs actual value
       - severity: CRITICAL, HIGH, MEDIUM, LOW
       - bbox: Tọa độ vùng lỗi
    
    Args:
        scan_job_id: ID duy nhất của job kiểm tra (UUID)
        side_name: Tên mặt đang kiểm tra ('side1' hoặc 'side2')
        camera_id: ID camera chụp ảnh này ('cam1' hoặc 'cam2')
        capture: Object chứa ảnh đã qua preprocess và metadata
            - content: Binary data của ảnh
            - filename: Tên file gốc
            - media_type: MIME type (image/jpeg, image/png, etc.)
        errors: Danh sách các lỗi phát hiện được từ comparison step
    
    Returns:
        dict[str, str]: Dictionary chứa đường dẫn tuyệt đối của 3 files:
            {
                "aligned_image": "/path/to/cam1_aligned.jpg",
                "annotated_image": "/path/to/cam1_annotated.png",
                "summary_json": "/path/to/cam1_summary.json"
            }
    
    Raises:
        OSError: Nếu không thể tạo thư mục hoặc ghi file
        IOError: Nếu không thể lưu ảnh hoặc JSON
    
    Examples:
        >>> capture = CaptureInput(
        ...     content=image_bytes,
        ...     filename="capture.jpg",
        ...     media_type="image/jpeg"
        ... )
        >>> errors = [
        ...     ComparisonError(
        ...         field_name="brand",
        ...         error_type=ErrorType.TEXT_MISMATCH,
        ...         expected_value="Nike",
        ...         actual_value="Adidas",
        ...         severity=Severity.CRITICAL,
        ...         bbox=BBox(x1=100, y1=200, x2=300, y2=250)
        ...     )
        ... ]
        >>> paths = save_evidence_artifacts(
        ...     scan_job_id="abc-123",
        ...     side_name="side1",
        ...     camera_id="cam1",
        ...     capture=capture,
        ...     errors=errors
        ... )
        >>> print(paths["annotated_image"])
        /storage/annotations/abc-123/side1/cam1_annotated.png
    
    Notes:
        - Thư mục evidence có thể chiếm nhiều dung lượng, cần cleanup định kỳ
        - Ảnh annotated lưu dạng PNG để giữ chất lượng bbox
        - JSON lưu với ensure_ascii=False để hỗ trợ tiếng Việt
        - Function này thread-safe vì mỗi scan_job_id có thư mục riêng
    """
    # Tạo thư mục theo cấu trúc: {storage}/annotations/{scan_job_id}/{side_name}/
    # VD: storage/annotations/abc-123/side1/
    side_folder = make_side_folder(ANNOTATION_STORAGE, scan_job_id, side_name)

    # 1) Lưu ảnh đã qua preprocess (aligned image)
    # Ảnh này đã qua: search window → localize → rectify → normalize
    # Đây là ảnh "sạch" nhất để làm input cho OCR và symbol detection
    raw_path = side_folder / _build_filename(camera_id, "aligned", capture)
    raw_path.write_bytes(capture.content)

    # 2) Lưu JSON summary chứa danh sách lỗi chi tiết
    # File này dùng để:
    # - API trả về cho frontend hiển thị
    # - Analyst review và phân tích xu hướng lỗi
    # - Training data cho việc cải thiện model
    summary_path = side_folder / f"{camera_id}_summary.json"
    write_json(
        summary_path,
        [
            {
                "field_name": error.field_name,              # Tên trường bị lỗi (VD: "brand", "size")
                "error_type": error.error_type.value,        # Loại lỗi (TEXT_MISMATCH, SYMBOL_MISSING, etc.)
                "expected_value": error.expected_value,      # Giá trị mong đợi từ template
                "actual_value": error.actual_value,          # Giá trị thực tế phát hiện được
                "severity": error.severity.value,            # Mức độ nghiêm trọng (CRITICAL, HIGH, MEDIUM, LOW)
                "message": error.message,                    # Message mô tả lỗi chi tiết
                "camera_source": error.camera_source,        # Camera nào phát hiện lỗi này
                "bbox": (
                    {
                        "x1": error.bbox.x1,                 # Tọa độ góc trên-trái
                        "y1": error.bbox.y1,
                        "x2": error.bbox.x2,                 # Tọa độ góc dưới-phải
                        "y2": error.bbox.y2,
                    }
                    if error.bbox
                    else None                                 # Một số lỗi không có bbox cụ thể
                ),
            }
            for error in errors
        ],
    )

    # 3) Lưu ảnh annotated (vẽ bbox đỏ tại vị trí lỗi)
    # Ảnh này giúp QA và operator nhanh chóng visualize các lỗi
    # mà không cần đọc JSON hoặc tính toán bbox
    annotated_path = side_folder / f"{camera_id}_annotated.png"
    _draw_error_boxes(capture, errors, annotated_path)

    return {
        "aligned_image": str(raw_path),
        "annotated_image": str(annotated_path),
        "summary_json": str(summary_path),
    }


# ══════════════════════════════════════════════════════════════════════════
# Backward-compat wrapper (giữ cho code cũ không bị break)
# ══════════════════════════════════════════════════════════════════════════

def save_annotation_summary(
    scan_job_id: str,
    side_name: str,
    camera_id: str,
    errors: list[ComparisonError],
) -> str:
    """
    [DEPRECATED] Wrapper cũ để tương thích ngược.
    
    Function này được giữ lại để code cũ không bị break ngay lập tức.
    Tuy nhiên, code mới nên dùng save_evidence_artifacts() thay thế
    vì nó lưu đầy đủ hơn (cả ảnh aligned và annotated).
    
    Args:
        scan_job_id: ID job kiểm tra
        side_name: Tên mặt ('side1' hoặc 'side2')
        camera_id: ID camera ('cam1' hoặc 'cam2')
        errors: Danh sách lỗi phát hiện được
    
    Returns:
        str: Đường dẫn file JSON đã lưu
    
    Notes:
        - Function này chỉ lưu JSON, không lưu ảnh
        - Sẽ bị remove trong version tương lai
        - Migration guide: Thay bằng save_evidence_artifacts()
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


# ══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════════

def _build_filename(camera_id: str, label: str, capture: CaptureInput) -> str:
    """
    Tạo tên file theo format chuẩn: {camera_id}_{label}{extension}
    
    Args:
        camera_id: ID camera (VD: 'cam1', 'cam2')
        label: Nhãn mô tả loại file (VD: 'aligned', 'raw', 'cropped')
        capture: Object chứa thông tin ảnh gốc
    
    Returns:
        str: Tên file theo format chuẩn
            VD: "cam1_aligned.jpg", "cam2_raw.png"
    
    Examples:
        >>> capture = CaptureInput(filename="photo.jpg", ...)
        >>> _build_filename("cam1", "aligned", capture)
        'cam1_aligned.jpg'
        
        >>> capture = CaptureInput(filename="image", ...)  # Không có extension
        >>> _build_filename("cam2", "raw", capture)
        'cam2_raw.bin'
    
    Notes:
        - Nếu file gốc không có extension, dùng '.bin' làm mặc định
        - Format này giúp dễ dàng identify file trong thư mục evidence
    """
    # Lấy extension từ filename gốc, nếu không có thì dùng .bin
    suffix = Path(capture.filename).suffix or ".bin"
    return f"{camera_id}_{label}{suffix}"


def _draw_error_boxes(
    capture: CaptureInput,
    errors: list[ComparisonError],
    output_path: Path,
) -> None:
    """
    Vẽ bounding box màu đỏ lên ảnh tại vị trí các lỗi phát hiện được.
    
    Function này xử lý 3 trường hợp:
    1. Ảnh thật + có Pillow: Vẽ bbox đỏ lên ảnh → lưu PNG
    2. Không phải ảnh (text, binary): Copy raw bytes
    3. Pillow chưa cài: Copy raw bytes (fallback)
    
    Luồng xử lý:
    1. Kiểm tra media_type có phải image không
    2. Thử import Pillow (PIL)
    3. Load ảnh từ bytes
    4. Vẽ rectangle đỏ (width=3px) tại mỗi bbox
    5. Lưu ảnh dạng PNG
    
    Args:
        capture: Object chứa ảnh và metadata
            - content: Binary data của ảnh
            - media_type: MIME type (VD: "image/jpeg", "image/png")
        errors: Danh sách lỗi, mỗi lỗi có thể có bbox
        output_path: Đường dẫn file output để lưu ảnh annotated
    
    Returns:
        None: Function này lưu file trực tiếp, không return gì
    
    Side Effects:
        - Tạo thư mục parent nếu chưa tồn tại
        - Ghi file ảnh annotated vào output_path
    
    Examples:
        >>> errors = [
        ...     ComparisonError(
        ...         field_name="brand",
        ...         bbox=BBox(x1=100, y1=200, x2=300, y2=250),
        ...         ...
        ...     ),
        ...     ComparisonError(
        ...         field_name="size",
        ...         bbox=BBox(x1=400, y1=300, x2=500, y2=350),
        ...         ...
        ...     )
        ... ]
        >>> _draw_error_boxes(capture, errors, Path("output.png"))
        # → Tạo file output.png với 2 bbox đỏ
    
    Notes:
        - Chỉ vẽ bbox cho errors có bbox không None
        - Màu đỏ (red) dễ nhận biết trên hầu hết background
        - Width=3px đủ rõ nhưng không che khuất nội dung
        - Lưu PNG để giữ chất lượng, không bị artifact như JPEG
        - Fallback về copy raw bytes nếu không thể vẽ (an toàn)
    """
    # Trường hợp 1: Không phải ảnh (text file, binary data, etc.)
    # → Chỉ copy raw bytes, không vẽ gì
    if not capture.media_type.startswith("image/"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(capture.content)
        return

    # Trường hợp 2: Pillow chưa được cài đặt
    # → Fallback về copy raw bytes để không crash
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(capture.content)
        return

    # Trường hợp 3: Ảnh thật + có Pillow → Vẽ bbox
    # Load ảnh từ bytes và convert sang RGB (đảm bảo 3 channels)
    image = Image.open(BytesIO(capture.content)).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Vẽ rectangle đỏ tại vị trí mỗi lỗi
    for error in errors:
        # Bỏ qua errors không có bbox (VD: lỗi logic không liên quan vị trí cụ thể)
        if error.bbox is None:
            continue
        
        # Vẽ rectangle với:
        # - outline="red": Viền màu đỏ dễ nhận biết
        # - width=3: Đủ rõ nhưng không che khuất nội dung
        draw.rectangle(
            [(error.bbox.x1, error.bbox.y1), (error.bbox.x2, error.bbox.y2)],
            outline="red",
            width=3,
        )

    # Lưu ảnh đã vẽ bbox ra file PNG
    # PNG giữ chất lượng tốt hơn JPEG cho việc visualize bbox
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
