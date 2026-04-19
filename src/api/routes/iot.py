"""
API routes cho IoT Events - Truy vấn log sự kiện IoT.

Module này cung cấp endpoints để:
1. Lấy danh sách IoT events đã publish cho một scan job
2. Debug và audit trail cho IoT integration

Endpoints:
    GET /api/iot/events/{scan_job_id}
        - Trả về tất cả IoT events đã publish cho scan job này
        - Bao gồm: topic, payload, timestamp, status (success/failed)

Use cases:
    - Debug IoT integration: Kiểm tra events đã được publish chưa
    - Audit trail: Truy vết lại các events đã gửi
    - Retry mechanism: Xác định events nào failed để retry
    - Monitoring: Theo dõi tỷ lệ thành công của IoT publish

IoT Event Flow:
    1. Inspection hoàn thành → Tạo event
    2. Publish event lên IoT broker (MQTT/HTTP)
    3. Lưu log vào database (success/failed)
    4. Retry nếu failed (với exponential backoff)
    5. API này cho phép query log để debug
"""
from __future__ import annotations

from src.api._compat import APIRouter, Depends, HTTPException
from src.api.deps import ApplicationContainer, get_container

router = APIRouter(prefix="/iot", tags=["iot"])


@router.get("/events/{scan_job_id}")
def get_iot_events(
    scan_job_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    """
    Lấy danh sách IoT events đã publish cho một scan job.
    
    Endpoint này trả về tất cả các events đã được publish
    (hoặc attempt publish) lên IoT broker cho scan job này.
    
    Mỗi event bao gồm:
    - topic: MQTT topic hoặc HTTP endpoint
    - payload: Nội dung event (JSON)
    - timestamp: Thời điểm publish
    - status: success/failed/pending
    - retry_count: Số lần đã retry
    - error_message: Lỗi nếu failed
    
    Response format:
        [
            {
                "event_id": "evt-123",
                "scan_job_id": "abc-123",
                "topic": "factory/line1/inspection/result",
                "payload": {
                    "scan_job_id": "abc-123",
                    "overall_decision": "FAIL",
                    "errors": [...]
                },
                "status": "success",
                "published_at": "2024-01-15T10:30:02",
                "retry_count": 0
            },
            {
                "event_id": "evt-124",
                "scan_job_id": "abc-123",
                "topic": "factory/line1/inspection/alert",
                "payload": {...},
                "status": "failed",
                "error_message": "Connection timeout",
                "retry_count": 3,
                "next_retry_at": "2024-01-15T10:35:00"
            }
        ]
    
    Args:
        scan_job_id: ID của scan job cần lấy events
        container: Application container (injected by FastAPI)
    
    Returns:
        list[dict]: Danh sách IoT events, sắp xếp theo thời gian
    
    Raises:
        HTTPException 500: Nếu có lỗi khi query database
    
    Examples:
        >>> GET /api/iot/events/abc-123
        [
            {
                "event_id": "evt-123",
                "topic": "factory/line1/inspection/result",
                "status": "success",
                "published_at": "2024-01-15T10:30:02"
            }
        ]
    
    Use cases:
        - Debug: Kiểm tra event đã được publish chưa
        - Audit: Truy vết lại các events đã gửi
        - Retry: Xác định events failed để manual retry
        - Monitoring: Dashboard hiển thị IoT health
    
    Notes:
        - Events được lưu vào bảng iot_events trong SQLite
        - Failed events sẽ được retry tự động với exponential backoff
        - Có thể thêm filter params trong tương lai:
          * status: success/failed/pending
          * topic: Filter theo topic cụ thể
    """
    try:
        return container.iot_event_repository.list_by_job(scan_job_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
