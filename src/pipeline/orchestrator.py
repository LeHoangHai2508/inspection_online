"""
Inspection Orchestrator - Điều phối luồng nghiệp vụ kiểm tra nhãn mác.

Module này là trung tâm điều phối toàn bộ quá trình inspection:
1. Quản lý state machine của scan job
2. Điều phối các bước: side1 → confirm → side2 → overall
3. Tích hợp các components: pipeline, decision, IoT, database
4. Enforce business rules và policies

State Machine Flow:
    WAIT_SIDE1_CAPTURE
        ↓ (inspect_side1)
    SIDE1_PROCESSING
        ↓
    SIDE1_DONE_WAIT_CONFIRM
        ↓ (confirm_side2)
    WAIT_SIDE2_CAPTURE
        ↓ (inspect_side2)
    SIDE2_PROCESSING
        ↓
    OVERALL_DONE

Components tích hợp:
    - TemplateService: Load template đã approved
    - InspectionPipeline: Xử lý ảnh và so sánh
    - OverallDecisionEngine: Quyết định PASS/FAIL/UNCERTAIN
    - OperatorActionDecider: Quyết định có cần operator review không
    - IoTAckService: Publish kết quả lên IoT broker
    - ScanResultRepository: Lưu kết quả vào database

Business Rules:
    - Không cho phép side2 nếu side1 đã NG (configurable)
    - Yêu cầu confirm thủ công giữa side1 và side2 (configurable)
    - Publish IoT event sau khi hoàn thành overall

Design Pattern:
    - Orchestrator pattern: Điều phối nhiều services
    - State machine: Quản lý trạng thái job
    - Dependency injection: Nhận dependencies qua constructor
"""
from __future__ import annotations

from src.decision.actions import OperatorActionDecider
from src.decision.rules import OverallDecisionEngine
from src.decision.severity import highest_severity
from src.db.repositories.scan_result_repo import SQLiteScanResultRepository
from src.domain.decision_schema import OrchestrationPolicy
from src.domain.enums import InspectionSide, InspectionStatus, RuntimeState
from src.domain.models import OverallInspectionResult, ScanJob, SideInspectionInput
from src.iot.ack_service import IoTAckService
from src.pipeline.inspection_pipeline import InspectionPipeline
from src.template_service.service import TemplateService


class InspectionOrchestrator:
    """
    Điều phối toàn bộ luồng nghiệp vụ inspection theo docs/plan.md.
    
    Class này là "conductor" của hệ thống, chịu trách nhiệm:
    1. Quản lý lifecycle của scan job (start → side1 → side2 → done)
    2. Enforce state machine (không cho phép skip steps)
    3. Điều phối các components (pipeline, decision, IoT, DB)
    4. Apply business policies (allow_side2_after_side1_ng, etc.)
    
    Attributes:
        _template_service: Service để load template
        _inspection_pipeline: Pipeline xử lý ảnh và so sánh
        _overall_decision_engine: Engine quyết định PASS/FAIL/UNCERTAIN
        _action_decider: Decider quyết định operator action
        _iot_ack_service: Service publish IoT events
        _scan_result_repository: Repository lưu kết quả vào DB
        _policy: Business policies (configurable)
        _jobs: In-memory cache của scan jobs đang chạy
    """

    def __init__(
        self,
        template_service: TemplateService,
        inspection_pipeline: InspectionPipeline | None = None,
        overall_decision_engine: OverallDecisionEngine | None = None,
        action_decider: OperatorActionDecider | None = None,
        iot_ack_service: IoTAckService | None = None,
        scan_result_repository: SQLiteScanResultRepository | None = None,
        policy: OrchestrationPolicy | None = None,
    ) -> None:
        """
        Khởi tạo InspectionOrchestrator với các dependencies.
        
        Args:
            template_service: Service để load template (required)
            inspection_pipeline: Pipeline xử lý ảnh (optional, default: new instance)
            overall_decision_engine: Engine quyết định overall (optional, default: new instance)
            action_decider: Decider quyết định operator action (optional, default: new instance)
            iot_ack_service: Service publish IoT (optional, default: new instance)
            scan_result_repository: Repository lưu DB (optional, default: None)
            policy: Business policies (optional, default: OrchestrationPolicy())
        
        Notes:
            - Chỉ template_service là required, các dependencies khác có default
            - Nếu scan_result_repository = None, kết quả không được persist vào DB
            - Policy mặc định:
              * allow_side2_after_side1_ng = True
              * require_manual_confirm_between_sides = True
        """
        self._template_service = template_service
        self._inspection_pipeline = inspection_pipeline or InspectionPipeline()
        self._overall_decision_engine = overall_decision_engine or OverallDecisionEngine()
        self._action_decider = action_decider or OperatorActionDecider()
        self._iot_ack_service = iot_ack_service or IoTAckService()
        self._scan_result_repository = scan_result_repository
        self._policy = policy or OrchestrationPolicy()
        
        # In-memory cache của scan jobs đang chạy
        # Key: scan_job_id, Value: ScanJob object
        self._jobs: dict[str, ScanJob] = {}

    def start_scan_job(
        self,
        scan_job_id: str,
        template_id: str,
        line_id: str = "LINE01",
        station_id: str = "ST01",
    ) -> ScanJob:
        """
        Bắt đầu một scan job mới.
        
        Function này:
        1. Validate template_id tồn tại và đã approved
        2. Tạo ScanJob object với state = WAIT_SIDE1_CAPTURE
        3. Lưu vào in-memory cache (_jobs)
        4. Persist vào database (nếu có repository)
        
        Args:
            scan_job_id: ID duy nhất của scan job (UUID)
            template_id: ID của template đã approved (VD: "TPL_001")
            line_id: ID của production line (default: "LINE01")
            station_id: ID của inspection station (default: "ST01")
        
        Returns:
            ScanJob: Object chứa thông tin job mới tạo
        
        Raises:
            ValueError: Nếu scan_job_id đã tồn tại
            LookupError: Nếu template_id không tồn tại hoặc chưa approved
        
        Examples:
            >>> orchestrator = InspectionOrchestrator(template_service)
            >>> job = orchestrator.start_scan_job(
            ...     scan_job_id="abc-123",
            ...     template_id="TPL_001",
            ...     line_id="LINE01"
            ... )
            >>> print(job.state)
            RuntimeState.WAIT_SIDE1_CAPTURE
        
        Notes:
            - Template phải ở trạng thái APPROVED, không chấp nhận REVIEW_REQUIRED
            - scan_job_id phải unique, không được trùng với jobs đang chạy
            - Job được lưu vào _jobs dict để track state
        """
        # Validate template tồn tại và đã approved
        self._template_service.get_approved_template(template_id)

        # Kiểm tra scan_job_id chưa tồn tại
        if scan_job_id in self._jobs:
            raise ValueError(f"Scan job '{scan_job_id}' already exists.")

        # Tạo ScanJob object với state ban đầu = WAIT_SIDE1_CAPTURE
        job = ScanJob(
            scan_job_id=scan_job_id,
            template_id=template_id,
            line_id=line_id,
            station_id=station_id,
        )
        
        # Lưu vào in-memory cache
        self._jobs[scan_job_id] = job
        
        # Persist vào database (nếu có repository)
        if self._scan_result_repository is not None:
            self._scan_result_repository.start_job(
                scan_job_id=scan_job_id,
                template_id=template_id,
                current_stage=job.state.value,
                line_id=line_id,
                station_id=station_id,
            )
        
        return job

    def inspect_side1(
        self,
        scan_job_id: str,
        inspection_input: SideInspectionInput,
    ):
        """
        Kiểm tra mặt 1 của nhãn mác.
        
        Function này thực hiện toàn bộ pipeline cho side1:
        1. Validate state = WAIT_SIDE1_CAPTURE
        2. Chuyển state → SIDE1_PROCESSING
        3. Load template đã approved
        4. Chạy inspection pipeline:
           - Preprocess: crop, quality gate, rectify
           - OCR: Nhận dạng text
           - Symbol detection: Nhận dạng ký hiệu
           - Compare: So sánh với template
        5. Lưu kết quả vào job.side1_result
        6. Chuyển state → SIDE1_DONE_WAIT_CONFIRM
        7. Persist kết quả vào database
        
        Args:
            scan_job_id: ID của scan job
            inspection_input: Input chứa ảnh và metadata
                - side: Phải là SIDE1
                - captures: List ảnh từ các cameras
        
        Returns:
            SideInspectionResult: Kết quả kiểm tra side1
                - status: OK/NG/UNCERTAIN
                - errors: Danh sách lỗi phát hiện được
                - ocr_result: Kết quả OCR
                - symbol_result: Kết quả symbol detection
        
        Raises:
            ValueError: Nếu inspection_input.side != SIDE1
            ValueError: Nếu job không ở state WAIT_SIDE1_CAPTURE
            LookupError: Nếu scan_job_id không tồn tại
        
        Examples:
            >>> input = SideInspectionInput(
            ...     side=InspectionSide.SIDE1,
            ...     captures=[capture1, capture2]
            ... )
            >>> result = orchestrator.inspect_side1("abc-123", input)
            >>> print(result.status)
            InspectionStatus.OK
        
        Notes:
            - Function này blocking, có thể mất 1-2 giây
            - Kết quả được lưu vào job.side1_result
            - State machine tự động chuyển sang SIDE1_DONE_WAIT_CONFIRM
            - Sau khi xong, cần gọi confirm_side2() trước khi inspect_side2()
        """
        # Validate input side phải là SIDE1
        if inspection_input.side != InspectionSide.SIDE1:
            raise ValueError("inspect_side1 only accepts side1 input.")

        # Lấy job và validate state
        job = self._get_job(scan_job_id)
        self._ensure_state(job, RuntimeState.WAIT_SIDE1_CAPTURE)
        
        # Chuyển state sang PROCESSING
        job.state = RuntimeState.SIDE1_PROCESSING
        self._update_stage(job)

        # Load template đã approved
        template = self._template_service.get_approved_template(job.template_id)
        
        # Chạy inspection pipeline
        job.side1_result = self._inspection_pipeline.inspect_side(
            template,
            inspection_input,
            scan_job_id=scan_job_id,
        )
        
        # Chuyển state sang DONE_WAIT_CONFIRM
        job.state = RuntimeState.SIDE1_DONE_WAIT_CONFIRM
        self._update_stage(job)
        
        # Persist kết quả vào database
        self._save_side_result(scan_job_id, job.side1_result)
        
        return job.side1_result

    def confirm_side2(self, scan_job_id: str) -> ScanJob:
        """
        Xác nhận tiếp tục kiểm tra mặt 2.
        
        Function này là bước trung gian giữa side1 và side2:
        1. Validate state = SIDE1_DONE_WAIT_CONFIRM
        2. Kiểm tra policy: Có cho phép side2 nếu side1 đã NG không?
        3. Chuyển state → WAIT_SIDE2_CAPTURE
        
        Mục đích:
        - Cho phép operator review kết quả side1 trước khi tiếp tục
        - Enforce business rule: Có thể stop ngay nếu side1 đã NG
        - Tạo checkpoint trong state machine
        
        Args:
            scan_job_id: ID của scan job
        
        Returns:
            ScanJob: Job object sau khi confirm
        
        Raises:
            ValueError: Nếu job không ở state SIDE1_DONE_WAIT_CONFIRM
            ValueError: Nếu policy không cho phép side2 khi side1 NG
            LookupError: Nếu scan_job_id không tồn tại
        
        Examples:
            >>> # Trường hợp 1: side1 OK → Cho phép side2
            >>> job = orchestrator.confirm_side2("abc-123")
            >>> print(job.state)
            RuntimeState.WAIT_SIDE2_CAPTURE
            
            >>> # Trường hợp 2: side1 NG + policy block → Raise error
            >>> orchestrator._policy.allow_side2_after_side1_ng = False
            >>> orchestrator.confirm_side2("abc-124")
            ValueError: Policy blocks side2 when side1 is already NG.
        
        Notes:
            - Policy mặc định: allow_side2_after_side1_ng = True
            - Nếu policy = False và side1 NG, function raise ValueError
            - Sau khi confirm, có thể gọi inspect_side2()
        """
        # Lấy job và validate state
        job = self._get_job(scan_job_id)
        self._ensure_state(job, RuntimeState.SIDE1_DONE_WAIT_CONFIRM)

        # Kiểm tra policy: Có cho phép side2 nếu side1 đã NG không?
        if (
            not self._policy.allow_side2_after_side1_ng
            and job.side1_result
            and job.side1_result.status == InspectionStatus.NG
        ):
            raise ValueError("Policy blocks side2 when side1 is already NG.")

        # Chuyển state sang WAIT_SIDE2_CAPTURE
        job.state = RuntimeState.WAIT_SIDE2_CAPTURE
        self._update_stage(job)
        
        return job

    def inspect_side2(
        self,
        scan_job_id: str,
        inspection_input: SideInspectionInput,
    ) -> OverallInspectionResult:
        """
        Kiểm tra mặt 2 và tạo kết quả tổng hợp (overall result).
        
        Function này là bước cuối cùng trong inspection flow:
        1. Validate state = WAIT_SIDE2_CAPTURE (hoặc SIDE1_DONE_WAIT_CONFIRM nếu skip confirm)
        2. Chuyển state → SIDE2_PROCESSING
        3. Chạy inspection pipeline cho side2
        4. Tổng hợp kết quả side1 + side2:
           - Overall decision: PASS/FAIL/UNCERTAIN
           - Merge errors từ cả 2 sides
           - Tính highest severity
           - Quyết định operator action required
        5. Publish IoT event
        6. Lưu overall result vào database
        7. Chuyển state → OVERALL_DONE
        
        Args:
            scan_job_id: ID của scan job
            inspection_input: Input chứa ảnh side2
                - side: Phải là SIDE2
                - captures: List ảnh từ các cameras
        
        Returns:
            OverallInspectionResult: Kết quả tổng hợp cuối cùng
                - scan_job_id: ID của job
                - template_id: Template đã dùng
                - side1_result: Kết quả side1
                - side2_result: Kết quả side2
                - overall_status: PASS/FAIL/UNCERTAIN
                - operator_action_required: True/False
                - highest_severity: CRITICAL/HIGH/MEDIUM/LOW
        
        Raises:
            ValueError: Nếu inspection_input.side != SIDE2
            ValueError: Nếu job không ở state đúng
            RuntimeError: Nếu side1_result chưa tồn tại
            LookupError: Nếu scan_job_id không tồn tại
        
        Examples:
            >>> input = SideInspectionInput(
            ...     side=InspectionSide.SIDE2,
            ...     captures=[capture1, capture2]
            ... )
            >>> result = orchestrator.inspect_side2("abc-123", input)
            >>> print(result.overall_status)
            InspectionStatus.PASS
            >>> print(result.operator_action_required)
            False
        
        Overall Decision Logic:
            - Nếu cả 2 sides OK → PASS
            - Nếu có 1 side NG → FAIL
            - Nếu có UNCERTAIN nhưng không có NG → UNCERTAIN
        
        Operator Action Logic:
            - CRITICAL errors → Always require action
            - HIGH errors + FAIL → Require action
            - UNCERTAIN → Require action
            - Otherwise → No action required
        
        Notes:
            - Function này blocking, có thể mất 1-2 giây
            - Sau khi xong, IoT event được publish tự động
            - Kết quả được persist vào database
            - State machine chuyển sang OVERALL_DONE (terminal state)
        """
        # Validate input side phải là SIDE2
        if inspection_input.side != InspectionSide.SIDE2:
            raise ValueError("inspect_side2 only accepts side2 input.")

        # Lấy job và validate state
        job = self._get_job(scan_job_id)
        
        # Expected state phụ thuộc vào policy
        # Nếu require_manual_confirm = True → Phải qua confirm_side2() trước
        # Nếu require_manual_confirm = False → Có thể skip confirm
        expected_state = (
            RuntimeState.WAIT_SIDE2_CAPTURE
            if self._policy.require_manual_confirm_between_sides
            else RuntimeState.SIDE1_DONE_WAIT_CONFIRM
        )
        self._ensure_state(job, expected_state)
        
        # Chuyển state sang PROCESSING
        job.state = RuntimeState.SIDE2_PROCESSING
        self._update_stage(job)

        # Load template và chạy inspection pipeline
        template = self._template_service.get_approved_template(job.template_id)
        job.side2_result = self._inspection_pipeline.inspect_side(
            template,
            inspection_input,
            scan_job_id=scan_job_id,
        )
        
        # Persist side2 result vào database
        self._save_side_result(scan_job_id, job.side2_result)

        # Validate side1_result đã tồn tại (không thể có side2 mà không có side1)
        if job.side1_result is None:
            raise RuntimeError("side1_result must exist before side2 is processed.")

        # ═══════════════════════════════════════════════════════════════
        # Tổng hợp kết quả overall
        # ═══════════════════════════════════════════════════════════════
        
        # 1. Quyết định overall status dựa trên side1 + side2
        overall_status = self._overall_decision_engine.decide(
            job.side1_result.status,
            job.side2_result.status,
        )
        
        # 2. Merge errors từ cả 2 sides
        all_errors = job.side1_result.errors + job.side2_result.errors
        
        # 3. Tìm severity cao nhất trong tất cả errors
        highest_error_severity = highest_severity(all_errors)
        
        # 4. Quyết định có cần operator review không
        operator_action = self._action_decider.decide(
            overall_status=overall_status,
            highest_error_severity=highest_error_severity,
        )

        # 5. Tạo OverallInspectionResult object
        # Đây là kết quả cuối cùng, chỉ được tạo khi cả 2 sides đã xong
        overall_result = OverallInspectionResult(
            scan_job_id=job.scan_job_id,
            template_id=job.template_id,
            side1_result=job.side1_result,
            side2_result=job.side2_result,
            overall_status=overall_status,
            operator_action_required=operator_action,
            highest_severity=highest_error_severity,
            publish_to_iot=True,
        )
        
        # 6. Lưu vào job object
        job.overall_result = overall_result
        
        # 7. Chuyển state sang OVERALL_DONE (terminal state)
        job.state = RuntimeState.OVERALL_DONE
        self._update_stage(job)
        
        # 8. Persist overall result vào database
        if self._scan_result_repository is not None:
            self._scan_result_repository.save_overall_result(overall_result)
        
        # 9. Publish IoT event (async, không block)
        self._iot_ack_service.publish_result(overall_result)
        
        return overall_result

    def get_job(self, scan_job_id: str) -> ScanJob:
        return self._get_job(scan_job_id)

    def get_result(self, scan_job_id: str) -> OverallInspectionResult:
        job = self._get_job(scan_job_id)
        if job.overall_result is None:
            raise LookupError(f"Scan job '{scan_job_id}' does not have final result yet.")
        return job.overall_result

    def _get_job(self, scan_job_id: str) -> ScanJob:
        try:
            return self._jobs[scan_job_id]
        except KeyError as exc:
            raise LookupError(f"Scan job '{scan_job_id}' does not exist.") from exc

    @staticmethod
    def _ensure_state(job: ScanJob, expected_state: RuntimeState) -> None:
        if job.state != expected_state:
            raise ValueError(
                f"Scan job '{job.scan_job_id}' is in state '{job.state}' "
                f"instead of '{expected_state}'."
            )

    def _update_stage(self, job: ScanJob) -> None:
        if self._scan_result_repository is not None:
            self._scan_result_repository.update_stage(
                scan_job_id=job.scan_job_id,
                current_stage=job.state.value,
            )

    def _save_side_result(
        self,
        scan_job_id: str,
        result,
    ) -> None:
        if self._scan_result_repository is not None and result is not None:
            self._scan_result_repository.save_side_result(scan_job_id, result)
