"""
API routes cho Counter Service - Thống kê và KPI.

Module này cung cấp các endpoints để:
1. Lấy tổng hợp KPI (total, OK, NG, UNCERTAIN, error_rate)
2. Lấy danh sách scan jobs gần đây cho dashboard

Endpoints:
    GET /api/counter/summary
        - Trả về KPI tổng hợp: tổng số, số OK, số NG, tỷ lệ lỗi
        - Dùng cho dashboard hiển thị số liệu tổng quan
        
    GET /api/counter/recent?limit=10
        - Trả về N scan jobs gần nhất
        - Dùng cho bảng history trên dashboard

Use cases:
    - Dashboard real-time: Hiển thị KPI tổng quan
    - History table: Hiển thị danh sách jobs gần đây
    - Monitoring: Theo dõi tỷ lệ lỗi theo thời gian
"""
from __future__ import annotations

from src.api._compat import APIRouter, Depends, HTTPException
from src.api.deps import ApplicationContainer, get_container

router = APIRouter(prefix="/counter", tags=["counter"])


@router.get("/summary")
def get_summary(container: ApplicationContainer = Depends(get_container)):
    """
    Lấy tổng hợp KPI cho dashboard.
    
    Endpoint này trả về các chỉ số thống kê tổng quan:
    - total: Tổng số scan jobs đã thực hiện
    - ok_count: Số lượng PASS
    - ng_count: Số lượng FAIL
    - uncertain_count: Số lượng UNCERTAIN (cần review thủ công)
    - error_rate: Tỷ lệ lỗi (ng_count / total)
    
    Response format:
        {
            "total": 1000,
            "ok_count": 850,
            "ng_count": 120,
            "uncertain_count": 30,
            "error_rate": 0.12
        }
    
    Use cases:
        - Dashboard hiển thị KPI cards
        - Monitoring tỷ lệ lỗi real-time
        - Báo cáo tổng quan cho management
    
    Returns:
        dict: KPI summary với các trường như trên
    
    Raises:
        HTTPException 500: Nếu có lỗi khi query database
    
    Examples:
        >>> GET /api/counter/summary
        {
            "total": 1000,
            "ok_count": 850,
            "ng_count": 120,
            "uncertain_count": 30,
            "error_rate": 0.12
        }
    """
    try:
        return container.counter_service.get_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/recent")
def get_recent(
    limit: int = 10,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Lấy danh sách N scan jobs gần nhất.
    
    Endpoint này trả về danh sách các scan jobs gần đây nhất,
    sắp xếp theo thời gian giảm dần (mới nhất trước).
    
    Dùng cho:
    - Bảng history trên dashboard
    - Recent activity feed
    - Quick access đến các jobs vừa thực hiện
    
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
        limit: Số lượng jobs tối đa (default: 10, max: 100)
        container: Application container (injected by FastAPI)
    
    Returns:
        list[dict]: Danh sách scan jobs, mỗi job là một dictionary
    
    Raises:
        HTTPException 500: Nếu có lỗi khi query database
    
    Examples:
        >>> GET /api/counter/recent?limit=5
        [
            {
                "scan_job_id": "abc-123",
                "overall_decision": "PASS",
                "created_at": "2024-01-15T10:30:00"
            },
            ...
        ]
    
    Notes:
        - Kết quả được cache trong 5 giây để giảm load database
        - Limit tối đa là 100 để tránh response quá lớn
        - Sắp xếp theo created_at DESC
    """
    try:
        return container.counter_service.get_recent_jobs(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
