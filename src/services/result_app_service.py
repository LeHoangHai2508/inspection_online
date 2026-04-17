"""
Result Application Service
────────────────────────────────────────────────────────────────────────────────
Service tổng hợp dữ liệu kết quả và lịch sử để hiển thị trên dashboard và
trang history. Kết hợp dữ liệu từ counter service và IoT event repository.
"""
from __future__ import annotations

from src.counter.service import CounterService
from src.db.repositories.iot_event_repo import SQLiteIoTEventRepository


class ResultAppService:
    """
    Application service cho dashboard và history.
    
    Tổng hợp dữ liệu từ nhiều nguồn:
    - Counter service: KPI tổng hợp (total, OK, NG, UNCERTAIN)
    - IoT event repo: Log các lần publish sang IoT
    """

    def __init__(
        self,
        counter_service: CounterService,
        iot_event_repository: SQLiteIoTEventRepository,
    ) -> None:
        """
        Khởi tạo service với counter và IoT repo.
        
        Args:
            counter_service: Service tính toán KPI từ DB
            iot_event_repository: Repository lưu log IoT publish
        """
        self._counter = counter_service
        self._iot_repo = iot_event_repository

    def get_dashboard_data(self) -> dict:
        """
        Lấy dữ liệu cho dashboard trang chủ.
        
        Bao gồm:
        - KPI tổng hợp: total, OK, NG, UNCERTAIN, error_rate_pct
        - 10 job gần nhất với status và action
        
        Returns:
            dict: {
                "summary": {
                    "total": int,
                    "ok": int,
                    "ng": int,
                    "uncertain": int,
                    "error_rate_pct": float
                },
                "recent_jobs": [
                    {
                        "scan_job_id": str,
                        "template_id": str,
                        "line_id": str,
                        "overall_status": str,
                        "operator_action_required": str,
                        "created_at": str
                    },
                    ...
                ]
            }
        """
        return {
            "summary": self._counter.get_summary(),
            "recent_jobs": self._counter.get_recent_jobs(limit=10),
        }

    def get_history(self, limit: int = 100) -> list[dict]:
        """
        Lấy danh sách job gần nhất cho trang history.
        
        Dữ liệu này có thể filter thêm ở controller layer theo:
        - Status (OK/NG/UNCERTAIN)
        - Template ID
        - Khoảng thời gian
        
        Args:
            limit: Số lượng job tối đa trả về (mặc định 100)
            
        Returns:
            list[dict]: Danh sách job, mỗi job chứa:
                - scan_job_id
                - template_id
                - line_id
                - current_stage
                - side1_status, side2_status
                - overall_status
                - operator_action_required
                - created_at
        """
        return self._counter.get_recent_jobs(limit=limit)

    def get_iot_events(self, scan_job_id: str) -> list[dict]:
        """
        Lấy log các lần publish IoT của một job.
        
        Mỗi job có thể có nhiều lần publish (retry nếu fail).
        Log này giúp debug khi IoT không nhận được event.
        
        Args:
            scan_job_id: ID của job cần xem log
            
        Returns:
            list[dict]: Danh sách event log, mỗi log chứa:
                - scan_job_id
                - action_type: loại action (CONTINUE, ALARM, STOP_LINE, RECHECK)
                - publish_status: "success" | "failed"
                - payload_path: đường dẫn file JSON đã ghi
                - retry_count: số lần retry
                - last_error: lỗi cuối cùng (nếu có)
                - created_at: thời gian publish
        """
        return self._iot_repo.list_by_job(scan_job_id)
