"""
Web Page Routes
────────────────────────────────────────────────────────────────────────────────
Các route render HTML page cho web UI (không phải API JSON).

Sử dụng Jinja2 templates để render HTML động với dữ liệu từ backend.
Tất cả page routes không có prefix (khác với API routes có prefix /api/).

Cấu trúc URL:
- /                              → Dashboard (KPI + recent jobs)
- /templates/upload              → Upload template mới
- /templates/{id}/review         → Review và approve template
- /inspect/side1                 → Trang kiểm tra mặt 1
- /inspect/{id}/confirm-side2    → Xác nhận chuyển mặt 2
- /inspect/side2                 → Trang kiểm tra mặt 2
- /result/{id}                   → Xem kết quả tổng hợp
- /history                       → Lịch sử kiểm tra với filter
"""
from __future__ import annotations

from src.api._compat import APIRouter, Depends, HTTPException, Request
from src.api.deps import ApplicationContainer, get_container
from src.api.serializers import to_primitive

# Import Jinja2 và setup templates directory
try:
    from fastapi.responses import HTMLResponse
    from fastapi.templating import Jinja2Templates
    from src.utils.paths import PROJECT_ROOT
    _templates = Jinja2Templates(directory=str(PROJECT_ROOT / "src" / "ui" / "templates"))
    _JINJA_OK = True
except Exception:  # pragma: no cover
    # Nếu không có Jinja2, các route vẫn register nhưng sẽ fail khi gọi
    _JINJA_OK = False

router = APIRouter(tags=["pages"])


def _render(request: Request, template: str, ctx: dict):
    """
    Helper function render Jinja2 template.
    
    Args:
        request: FastAPI Request object (bắt buộc cho Jinja2)
        template: Tên file template (vd: "home.html")
        ctx: Dict chứa data truyền vào template
        
    Returns:
        TemplateResponse với HTML đã render
        
    Raises:
        HTTPException 500: Nếu Jinja2 không available
    """
    if not _JINJA_OK:
        raise HTTPException(status_code=500, detail="Jinja2 / templates not available.")
    return _templates.TemplateResponse(template, {"request": request, **ctx})


@router.get("/", response_class=HTMLResponse if _JINJA_OK else None)
def home(request: Request, container: ApplicationContainer = Depends(get_container)):
    """
    Trang Dashboard — trang chủ của hệ thống.
    
    Hiển thị:
    - 5 KPI cards: Total, OK, NG, UNCERTAIN, Error Rate
    - Bảng 10 job gần nhất với status và action
    - Trạng thái line hiện tại (Running/Stop)
    
    Template: home.html
    
    Returns:
        HTML page với data:
            - summary: {total, ok, ng, uncertain, error_rate_pct}
            - recent_jobs: list 10 job gần nhất
            - line_status: "Running" (hardcode, có thể lấy từ IoT sau)
    """
    summary = container.counter_service.get_summary()
    recent = container.counter_service.get_recent_jobs(limit=10)
    return _render(request, "home.html", {
        "summary": summary,
        "recent_jobs": recent,
        "line_status": "Running",
    })


@router.get("/templates", response_class=HTMLResponse if _JINJA_OK else None)
def templates_list(request: Request, container: ApplicationContainer = Depends(get_container)):
    """
    Trang danh sách template (chưa implement).
    
    Hiện tại redirect về trang upload.
    Sau này có thể thêm bảng list tất cả template với filter.
    
    Returns:
        Redirect 302 → /templates/upload
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/templates/upload")


@router.get("/templates/upload", response_class=HTMLResponse if _JINJA_OK else None)
def template_upload_page(request: Request):
    """
    Trang upload template mới.
    
    Form upload bao gồm:
    - Template Name
    - Product Code
    - Side1 file (image/PDF)
    - Side2 file (image/PDF)
    
    Sau khi upload, hệ thống sẽ:
    1. OCR full cả 2 mặt
    2. Tạo template với status = DRAFT
    3. Redirect về trang review
    
    Template: template_review.html (dùng chung với review page)
    
    Returns:
        HTML form upload với preview rỗng
    """
    return _render(request, "template_review.html", {
        "template": {"template_id": "", "status": "DRAFT"},
        "preview": {
            "side1_raw_text": "", "side2_raw_text": "",
            "fields_by_side": {"side1": [], "side2": []},
            "unmapped_blocks": {"side1": [], "side2": []},
            "original_file_paths": {"side1": None, "side2": None},
        },
    })


@router.get("/templates/{template_id}/review", response_class=HTMLResponse if _JINJA_OK else None)
def template_review_page(
    template_id: str,
    request: Request,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Trang review template sau khi upload.
    
    Hiển thị:
    - Ảnh gốc side1 và side2
    - OCR raw text của cả 2 mặt
    - Bảng field đã map (có thể edit trực tiếp)
    - Warning nếu có block chưa map hoặc confidence thấp
    - Nút Approve / Reject
    
    Người dùng có thể:
    - Sửa field_name, expected_value, compare_type, priority
    - Thêm field mới
    - Xóa field không cần
    - Save draft hoặc approve luôn
    
    Template: template_review.html
    
    Args:
        template_id: ID của template cần review
        
    Returns:
        HTML page với data:
            - template: record với status, metadata
            - preview: OCR text, fields, unmapped blocks, file paths
            
    Raises:
        HTTPException 404: Nếu template không tồn tại
    """
    try:
        record = container.template_service.get_template(template_id)
        preview = container.template_service.get_template_preview(template_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _render(request, "template_review.html", {
        "template": to_primitive(record),
        "preview": preview,
    })


@router.get("/inspect/side1", response_class=HTMLResponse if _JINJA_OK else None)
def inspect_side1_page(request: Request, scan_job_id: str = "", template_id: str = ""):
    """
    Trang kiểm tra mặt 1.
    
    Form bao gồm:
    - Scan Job ID (tự sinh hoặc nhập thủ công)
    - Template ID (chọn từ danh sách template đã approve)
    - Upload cam1 image
    - Upload cam2 image
    - Nút "Inspect Side1" (upload mode)
    - Nút "Live Camera" (chụp trực tiếp từ camera)
    
    Sau khi inspect xong:
    - Hiển thị kết quả side1 (status, errors, processing time)
    - Tự động redirect sang trang confirm-side2
    
    Template: side1.html
    
    Args:
        scan_job_id: ID của job (optional, có thể để trống)
        template_id: ID của template (optional)
        
    Returns:
        HTML form inspect side1
    """
    return _render(request, "side1.html", {
        "scan_job_id": scan_job_id,
        "template_id": template_id,
    })


@router.get("/inspect/{scan_job_id}/confirm-side2", response_class=HTMLResponse if _JINJA_OK else None)
def confirm_side2_page(
    scan_job_id: str,
    request: Request,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Trang xác nhận chuyển mặt 2.
    
    Hiển thị:
    - Kết quả side1 (status, errors)
    - Hướng dẫn: "Lật tem sang mặt 2 rồi nhấn xác nhận"
    - Nút lớn "Xác nhận chuyển mặt 2"
    
    Đây là bước thủ công bắt buộc — người vận hành phải:
    1. Xem kết quả side1
    2. Lật tem sang mặt 2
    3. Bấm nút xác nhận
    
    Template: confirm_side2.html
    
    Args:
        scan_job_id: ID của job đang chạy
        
    Returns:
        HTML page với data:
            - scan_job_id
            - result: side1_result (status, errors)
            
    Raises:
        HTTPException 404: Nếu job không tồn tại
    """
    try:
        job = container.inspection_orchestrator.get_job(scan_job_id)
        side1_result = to_primitive(job.side1_result) if job.side1_result else {}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _render(request, "confirm_side2.html", {
        "scan_job_id": scan_job_id,
        "result": side1_result,
    })


@router.post("/inspect/{scan_job_id}/confirm-side2", response_class=HTMLResponse if _JINJA_OK else None)
def confirm_side2_submit(
    scan_job_id: str,
    request: Request,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Xử lý submit form xác nhận chuyển mặt 2.
    
    Khi user bấm nút "Xác nhận chuyển mặt 2":
    1. Gọi orchestrator.confirm_side2()
    2. State chuyển từ SIDE1_DONE_WAIT_CONFIRM → WAIT_SIDE2_CAPTURE
    3. Redirect sang trang inspect side2
    
    Args:
        scan_job_id: ID của job đang chạy
        
    Returns:
        Redirect 303 → /inspect/side2?scan_job_id=...&template_id=...
        
    Raises:
        HTTPException 400: Nếu job không ở đúng state hoặc policy không cho phép
    """
    from fastapi.responses import RedirectResponse
    try:
        job = container.inspection_orchestrator.confirm_side2(scan_job_id)
        template_id = job.template_id
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(
        url=f"/inspect/side2?scan_job_id={scan_job_id}&template_id={template_id}",
        status_code=303,
    )


@router.get("/inspect/side2", response_class=HTMLResponse if _JINJA_OK else None)
def inspect_side2_page(request: Request, scan_job_id: str = "", template_id: str = ""):
    """
    Trang kiểm tra mặt 2.
    
    Form tương tự side1:
    - Upload cam1 image
    - Upload cam2 image
    - Nút "Inspect Side2" (upload mode)
    - Nút "Live Camera" (chụp trực tiếp)
    
    Sau khi inspect xong:
    - Hiển thị kết quả side2
    - Tự động redirect sang trang result (overall)
    
    Template: side2.html
    
    Args:
        scan_job_id: ID của job (từ confirm page)
        template_id: ID của template (từ confirm page)
        
    Returns:
        HTML form inspect side2
    """
    return _render(request, "side2.html", {
        "scan_job_id": scan_job_id,
        "template_id": template_id,
    })


@router.get("/result/{scan_job_id}", response_class=HTMLResponse if _JINJA_OK else None)
def result_page(
    scan_job_id: str,
    request: Request,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Trang kết quả tổng hợp.
    
    Hiển thị:
    - Overall status (OK/NG/UNCERTAIN) với màu sắc rõ ràng
    - Operator action required (CONTINUE/ALARM/STOP_LINE/RECHECK)
    - Highest severity
    - Side1 result: status, errors, ảnh annotate cam1+cam2
    - Side2 result: status, errors, ảnh annotate cam1+cam2
    - Processing time của từng mặt
    
    Template: result.html
    
    Args:
        scan_job_id: ID của job cần xem kết quả
        
    Returns:
        HTML page với data:
            - result: OverallInspectionResult đầy đủ
            
    Raises:
        HTTPException 404: Nếu job không tồn tại hoặc chưa có overall result
    """
    try:
        result = container.inspection_orchestrator.get_result(scan_job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _render(request, "result.html", {"result": to_primitive(result)})


@router.get("/history", response_class=HTMLResponse if _JINJA_OK else None)
def history_page(
    request: Request,
    status: str = "",
    template_id: str = "",
    date_from: str = "",
    date_to: str = "",
    container: ApplicationContainer = Depends(get_container),
):
    """
    Trang lịch sử kiểm tra.
    
    Hiển thị:
    - Bộ lọc: status, template_id, date range
    - Bảng danh sách job với các cột:
      * Scan Job ID (link đến trang result)
      * Template ID
      * Line ID
      * Side1 Status
      * Side2 Status
      * Overall Status (badge màu)
      * Operator Action
      * Created At
    
    Filter logic:
    - Nếu có status → chỉ hiển thị job có overall_status = status
    - Nếu có template_id → search theo substring (case-insensitive)
    - date_from, date_to: chưa implement (có thể thêm sau)
    
    Template: history.html
    
    Args:
        status: Filter theo overall_status (optional)
        template_id: Filter theo template_id (optional)
        date_from: Filter từ ngày (optional, chưa dùng)
        date_to: Filter đến ngày (optional, chưa dùng)
        
    Returns:
        HTML page với data:
            - jobs: list job đã filter
            - filters: dict chứa giá trị filter hiện tại
    """
    jobs = container.counter_service.get_recent_jobs(limit=100)
    
    # Apply filters
    if status:
        jobs = [j for j in jobs if j.get("overall_status") == status]
    if template_id:
        jobs = [j for j in jobs if template_id.lower() in (j.get("template_id") or "").lower()]
    
    return _render(request, "history.html", {
        "jobs": jobs,
        "filters": {
            "status": status,
            "template_id": template_id,
            "date_from": date_from,
            "date_to": date_to,
        },
    })
