"""
IoT Application Service
────────────────────────────────────────────────────────────────────────────────
Service xử lý publish kết quả kiểm tra sang hệ thống IoT và quản lý log publish.

Chức năng:
- Publish overall result sang IoT (HTTP/MQTT/Mock)
- Lưu log mỗi lần publish để audit
- Retry khi publish fail
"""
from __future__ import annotations

from src.db.repositories.iot_event_repo import SQLiteIoTEventRepository
from src.domain.models import OverallInspectionResult
from src.iot.ack_service import IoTAckService
from src.iot.event_builder import build_iot_event


class IoTAppService:
    """
    Application service cho IoT integration.
    
    Xử lý việc gửi kết quả kiểm tra sang hệ thống IoT bên ngoài
    và lưu log để tracking.
    """

    def __init__(
        self,
        ack_service: IoTAckService,
        iot_event_repository: SQLiteIoTEventRepository,
    ) -> None:
        """
        Khởi tạo service với ack service và event repo.
        
        Args:
            ack_service: Service publish event sang IoT
            iot_event_repository: Repository lưu log publish
        """
        self._ack = ack_service
        self._repo = iot_event_repository

    def publish(self, result: OverallInspectionResult) -> dict:
        """
        Publish kết quả kiểm tra sang IoT.
        
        Luồng xử lý:
        1. Build IoT event từ overall result
        2. Publish qua ack_service (HTTP/MQTT/Mock tùy config)
        3. Log kết quả publish vào DB
        
        Event payload gửi đi bao gồm:
        - scan_job_id
        - template_id
        - overall_status: OK | NG | UNCERTAIN
        - operator_action_required: CONTINUE | ALARM | STOP_LINE | RECHECK
        - highest_severity: critical | major | minor
        
        Args:
            result: OverallInspectionResult sau khi kiểm tra xong side2
            
        Returns:
            dict: Event đã build (để debug/log)
            
        Note:
            - Nếu publish fail, ack_service sẽ tự động retry theo config
            - Log được ghi vào bảng iot_publish_logs
        """
        event = build_iot_event(result)
        self._ack.publish_result(result)
        return event

    def get_logs(self, scan_job_id: str) -> list[dict]:
        """
        Lấy log các lần publish IoT của một job.
        
        Dùng để:
        - Debug khi IoT không nhận được event
        - Audit trail — xem job nào đã publish thành công
        - Kiểm tra retry count
        
        Args:
            scan_job_id: ID của job cần xem log
            
        Returns:
            list[dict]: Danh sách log, mỗi log chứa:
                - scan_job_id
                - action_type: CONTINUE | ALARM | STOP_LINE | RECHECK
                - publish_status: "success" | "failed"
                - payload_path: đường dẫn file JSON (nếu mode=mock)
                - retry_count: số lần đã retry
                - last_error: message lỗi cuối (nếu fail)
                - created_at: timestamp
        """
        return self._repo.list_by_job(scan_job_id)
