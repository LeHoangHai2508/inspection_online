"""
Inspection Application Service
────────────────────────────────────────────────────────────────────────────────
Service lớp ứng dụng cho luồng kiểm tra runtime — quản lý state machine của
việc kiểm tra 2 mặt tem theo thứ tự: side1 → confirm → side2 → overall.

Luồng chuẩn:
1. start_job() — tạo scan job mới
2. inspect_side1() — kiểm tra mặt 1
3. confirm_side2() — xác nhận chuyển mặt 2
4. inspect_side2() — kiểm tra mặt 2
5. get_result() — lấy kết quả tổng hợp
"""
from __future__ import annotations

from src.api.serializers import to_primitive
from src.domain.models import SideInspectionInput
from src.pipeline.orchestrator import InspectionOrchestrator


class InspectionAppService:
    """
    Application service cho runtime inspection flow.
    
    Wrap InspectionOrchestrator để:
    - Controller không cần biết state machine phức tạp
    - Tự động serialize kết quả thành JSON
    - Đơn giản hóa error handling
    """

    def __init__(self, orchestrator: InspectionOrchestrator) -> None:
        """
        Khởi tạo service với orchestrator.
        
        Args:
            orchestrator: Domain orchestrator quản lý state machine inspection
        """
        self._orch = orchestrator

    def start_job(self, scan_job_id: str, template_id: str) -> dict:
        """
        Bắt đầu một scan job mới.
        
        Tạo job với state ban đầu = WAIT_SIDE1_CAPTURE.
        Validate template_id phải là template đã APPROVED.
        
        Args:
            scan_job_id: ID duy nhất của job (vd: "LINE01_ST01_000123")
            template_id: ID của template đã approve
            
        Returns:
            dict: {
                "scan_job_id": str,
                "state": "WAIT_SIDE1_CAPTURE"
            }
            
        Raises:
            ValueError: Nếu scan_job_id đã tồn tại
            LookupError: Nếu template không tồn tại hoặc chưa approve
        """
        job = self._orch.start_scan_job(
            scan_job_id=scan_job_id,
            template_id=template_id,
        )
        return {"scan_job_id": job.scan_job_id, "state": job.state.value}

    def inspect_side1(self, scan_job_id: str, inspection_input: SideInspectionInput) -> dict:
        """
        Kiểm tra mặt 1 của tem.
        
        Luồng xử lý:
        1. Validate job đang ở state WAIT_SIDE1_CAPTURE
        2. Chuyển state → SIDE1_PROCESSING
        3. Crop ROI từ ảnh cam1 + cam2
        4. Quality gate check (blur, brightness, crop thiếu)
        5. OCR full text từ cả 2 camera
        6. Normalize text
        7. Compare với template side1
        8. Tổng hợp lỗi và ra quyết định: OK | NG | UNCERTAIN
        9. Annotate ảnh (vẽ bbox lỗi)
        10. Lưu kết quả vào DB
        11. Chuyển state → SIDE1_DONE_WAIT_CONFIRM
        
        Args:
            scan_job_id: ID của job đang chạy
            inspection_input: Input chứa:
                - side: SIDE1
                - captures: [CaptureInput(cam1), CaptureInput(cam2)]
                - observed_fields: (optional) field đã detect
                
        Returns:
            dict: SideInspectionResult serialize, bao gồm:
                {
                    "side": "side1",
                    "status": "OK" | "NG" | "UNCERTAIN",
                    "errors": [
                        {
                            "field_name": str,
                            "error_type": str,
                            "severity": "critical" | "major" | "minor",
                            "expected_value": str,
                            "actual_value": str,
                            "bbox": [x1, y1, x2, y2]
                        }
                    ],
                    "raw_text": str,
                    "processing_time_ms": int,
                    "annotated_assets": {"cam1": path, "cam2": path}
                }
                
        Raises:
            ValueError: Nếu job không ở đúng state
            LookupError: Nếu job không tồn tại
        """
        result = self._orch.inspect_side1(scan_job_id, inspection_input)
        return to_primitive(result)

    def confirm_side2(self, scan_job_id: str) -> dict:
        """
        Xác nhận chuyển sang kiểm tra mặt 2.
        
        Đây là bước thủ công — người vận hành phải:
        1. Xem kết quả side1
        2. Lật tem sang mặt 2
        3. Bấm nút xác nhận
        
        Policy check:
        - Nếu config allow_side2_after_side1_ng = False và side1 = NG
          → Từ chối, không cho kiểm side2 nữa
        
        Args:
            scan_job_id: ID của job đang chạy
            
        Returns:
            dict: {
                "scan_job_id": str,
                "state": "WAIT_SIDE2_CAPTURE"
            }
            
        Raises:
            ValueError: Nếu job không ở state SIDE1_DONE_WAIT_CONFIRM
                       hoặc policy không cho phép
        """
        job = self._orch.confirm_side2(scan_job_id)
        return {"scan_job_id": job.scan_job_id, "state": job.state.value}

    def inspect_side2(self, scan_job_id: str, inspection_input: SideInspectionInput) -> dict:
        """
        Kiểm tra mặt 2 của tem và ra kết quả tổng hợp.
        
        Luồng xử lý:
        1. Validate job đang ở state WAIT_SIDE2_CAPTURE
        2. Chuyển state → SIDE2_PROCESSING
        3. Crop ROI, quality gate, OCR, normalize, compare (giống side1)
        4. Lưu side2_result vào DB
        5. Tổng hợp side1 + side2 → overall decision:
           - Nếu side1 = OK và side2 = OK → overall = OK
           - Nếu side1 = NG hoặc side2 = NG → overall = NG
           - Nếu có ít nhất 1 mặt UNCERTAIN → overall = UNCERTAIN
        6. Xác định operator action dựa trên severity cao nhất:
           - OK → CONTINUE
           - NG + critical → STOP_LINE
           - NG + major → ALARM
           - UNCERTAIN → RECHECK
        7. Publish kết quả sang IoT
        8. Chuyển state → OVERALL_DONE
        
        Args:
            scan_job_id: ID của job đang chạy
            inspection_input: Input chứa captures của side2
            
        Returns:
            dict: OverallInspectionResult serialize, bao gồm:
                {
                    "scan_job_id": str,
                    "template_id": str,
                    "side1_result": {...},
                    "side2_result": {...},
                    "overall_status": "OK" | "NG" | "UNCERTAIN",
                    "operator_action_required": "CONTINUE" | "ALARM" | "STOP_LINE" | "RECHECK",
                    "highest_severity": "critical" | "major" | "minor",
                    "publish_to_iot": True
                }
                
        Raises:
            ValueError: Nếu job không ở đúng state
            RuntimeError: Nếu side1_result chưa có
        """
        result = self._orch.inspect_side2(scan_job_id, inspection_input)
        return to_primitive(result)

    def get_result(self, scan_job_id: str) -> dict:
        """
        Lấy kết quả tổng hợp cuối cùng của job.
        
        Chỉ có kết quả sau khi side2 đã xong (state = OVERALL_DONE).
        
        Args:
            scan_job_id: ID của job cần lấy kết quả
            
        Returns:
            dict: OverallInspectionResult serialize (giống output của inspect_side2)
            
        Raises:
            LookupError: Nếu job không tồn tại hoặc chưa có overall_result
        """
        result = self._orch.get_result(scan_job_id)
        return to_primitive(result)
