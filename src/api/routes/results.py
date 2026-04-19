"""
API routes cho Results - Truy vấn kết quả kiểm tra.

Module này cung cấp các endpoints để:
1. Lấy kết quả chi tiết của một scan job cụ thể
2. Lấy danh sách scan jobs gần đây (tương tự counter/recent)

Endpoints:
    GET /api/results/{scan_job_id}
        - Trả về kết quả đầy đủ của một scan job
        - Bao gồm: overall_decision, errors, side1_result, side2_result
        
    GET /api/results/?limit=10
        - Trả về danh sách scan jobs gần đây
        - Tương tự /api/counter/recent nhưng có thể filter thêm

Use cases:
    - Result page: Hiển thị kết quả chi tiết sau khi kiểm tra xong
    - History page: Xem lại kết quả các lần kiểm tra trước
    - API integration: External systems query kết quả
"""
from __future__ import annotations

import sqlite3

from src.api._compat import APIRouter, Depends, HTTPException
from src.api.deps import ApplicationContainer, get_container
from src.api.serializers import to_primitive

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{scan_job_id}")
def get_result(
    scan_job_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Lấy kết quả chi tiết của một scan job.
    
    Endpoint này trả về toàn bộ thông tin kết quả kiểm tra:
    - Overall decision: PASS/FAIL/UNCERTAIN
    - Side1 result: Kết quả kiểm tra mặt 1
    - Side2 result: Kết quả kiểm tra mặt 2
    - Errors: Danh sách lỗi phát hiện được
    - Metadata: Template ID, timestamps, etc.
    
    Response format:
        {
            "scan_job_id": "abc-123",
            "template_id": "TPL_001",
            "overall_decision": "FAIL",
            "side1_result": {
                "decision": "PASS",
                "errors": [],
                "ocr_result": {...},
                "quality_metrics": {...}
            },
            "side2_result": {
                "decision": "FAIL",
                "errors": [
                    {
                        "field_name": "brand",
                        "error_type": "TEXT_MISMATCH",
                        "expected_value": "Nike",
                        "actual_value": "Adidas",
                        "severity": "CRITICAL"
                    }
                ],
                "ocr_result": {...}
            },
            "created_at": "2024-01-15T10:30:00",
            "completed_at": "2024-01-15T10:30:02"
        }
    
    Args:
        scan_job_id: ID của scan job cần lấy kết quả
        container: Application container (injected by FastAPI)
    
    Returns:
        dict: Kết quả đầy đủ của scan job, đã serialize sang primitive types
    
    Raises:
        HTTPException 404: Nếu scan_job_id không tồn tại
        HTTPException 500: Nếu có lỗi khi query database
    
    Examples:
        >>> GET /api/results/abc-123
        {
            "scan_job_id": "abc-123",
            "overall_decision": "FAIL",
            "side1_result": {...},
            "side2_result": {...}
        }
    
    Notes:
        - Kết quả được serialize bằng to_primitive() để convert
          các object phức tạp (dataclass, enum) sang dict/list/str
        - Nếu job chưa hoàn thành, có thể trả về partial result
        - Evidence images không được include trong response này,
          cần gọi riêng endpoint /evidence/{scan_job_id}
    """
    try:
        result = container.inspection_orchestrator.get_result(scan_job_id)
        return to_primitive(result)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/")
def list_recent(
    limit: int = 10,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Lấy danh sách scan jobs gần đây với status.
    
    Endpoint này tương tự /api/counter/recent nhưng nằm dưới
    namespace /results để nhất quán với RESTful design.
    
    Dùng cho:
    - Dashboard feed: Hiển thị activity gần đây
    - History page: Danh sách các lần kiểm tra
    - Quick navigation: Jump đến result detail
    
    Query params:
        limit: Số lượng jobs tối đa trả về (default: 10)
    
    Response format:
        [
            {
                "scan_job_id": "abc-123",
                "template_id": "TPL_001",
                "overall_decision": "PASS",
                "created_at": "2024-01-15T10:30:00",
                "completed_at": "2024-01-15T10:30:02"
            },
            ...
        ]
    
    Args:
        limit: Số lượng jobs tối đa (default: 10)
        container: Application container (injected by FastAPI)
    
    Returns:
        list[dict]: Danh sách scan jobs với status
    
    Raises:
        HTTPException 500: Nếu có lỗi khi query database
    
    Examples:
        >>> GET /api/results/?limit=20
        [
            {
                "scan_job_id": "abc-123",
                "overall_decision": "PASS",
                "created_at": "2024-01-15T10:30:00"
            },
            ...
        ]
    
    Notes:
        - Endpoint này duplicate với /api/counter/recent
        - Trong tương lai có thể thêm filter params:
          * status: PASS/FAIL/UNCERTAIN
          * template_id: Filter theo template
          * date_range: Filter theo khoảng thời gian
    """
    try:
        return container.counter_service.get_recent_jobs(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
