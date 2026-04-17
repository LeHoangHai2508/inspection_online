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
    """Coordinates the business flow described in docs/plan.md."""

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
        self._template_service = template_service
        self._inspection_pipeline = inspection_pipeline or InspectionPipeline()
        self._overall_decision_engine = overall_decision_engine or OverallDecisionEngine()
        self._action_decider = action_decider or OperatorActionDecider()
        self._iot_ack_service = iot_ack_service or IoTAckService()
        self._scan_result_repository = scan_result_repository
        self._policy = policy or OrchestrationPolicy()
        self._jobs: dict[str, ScanJob] = {}

    def start_scan_job(
        self,
        scan_job_id: str,
        template_id: str,
        line_id: str = "LINE01",
        station_id: str = "ST01",
    ) -> ScanJob:
        self._template_service.get_approved_template(template_id)

        if scan_job_id in self._jobs:
            raise ValueError(f"Scan job '{scan_job_id}' already exists.")

        job = ScanJob(
            scan_job_id=scan_job_id,
            template_id=template_id,
            line_id=line_id,
            station_id=station_id,
        )
        self._jobs[scan_job_id] = job
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
        if inspection_input.side != InspectionSide.SIDE1:
            raise ValueError("inspect_side1 only accepts side1 input.")

        job = self._get_job(scan_job_id)
        self._ensure_state(job, RuntimeState.WAIT_SIDE1_CAPTURE)
        job.state = RuntimeState.SIDE1_PROCESSING
        self._update_stage(job)

        template = self._template_service.get_approved_template(job.template_id)
        job.side1_result = self._inspection_pipeline.inspect_side(
            template,
            inspection_input,
            scan_job_id=scan_job_id,
        )
        job.state = RuntimeState.SIDE1_DONE_WAIT_CONFIRM
        self._update_stage(job)
        self._save_side_result(scan_job_id, job.side1_result)
        return job.side1_result

    def confirm_side2(self, scan_job_id: str) -> ScanJob:
        job = self._get_job(scan_job_id)
        self._ensure_state(job, RuntimeState.SIDE1_DONE_WAIT_CONFIRM)

        if (
            not self._policy.allow_side2_after_side1_ng
            and job.side1_result
            and job.side1_result.status == InspectionStatus.NG
        ):
            raise ValueError("Policy blocks side2 when side1 is already NG.")

        job.state = RuntimeState.WAIT_SIDE2_CAPTURE
        self._update_stage(job)
        return job

    def inspect_side2(
        self,
        scan_job_id: str,
        inspection_input: SideInspectionInput,
    ) -> OverallInspectionResult:
        if inspection_input.side != InspectionSide.SIDE2:
            raise ValueError("inspect_side2 only accepts side2 input.")

        job = self._get_job(scan_job_id)
        expected_state = (
            RuntimeState.WAIT_SIDE2_CAPTURE
            if self._policy.require_manual_confirm_between_sides
            else RuntimeState.SIDE1_DONE_WAIT_CONFIRM
        )
        self._ensure_state(job, expected_state)
        job.state = RuntimeState.SIDE2_PROCESSING
        self._update_stage(job)

        template = self._template_service.get_approved_template(job.template_id)
        job.side2_result = self._inspection_pipeline.inspect_side(
            template,
            inspection_input,
            scan_job_id=scan_job_id,
        )
        self._save_side_result(scan_job_id, job.side2_result)

        if job.side1_result is None:
            raise RuntimeError("side1_result must exist before side2 is processed.")

        overall_status = self._overall_decision_engine.decide(
            job.side1_result.status,
            job.side2_result.status,
        )
        all_errors = job.side1_result.errors + job.side2_result.errors
        highest_error_severity = highest_severity(all_errors)
        operator_action = self._action_decider.decide(
            overall_status=overall_status,
            highest_error_severity=highest_error_severity,
        )

        # The final result is assembled only once both sides exist.
        # This keeps the state machine simple and avoids half-built records.
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
        job.overall_result = overall_result
        job.state = RuntimeState.OVERALL_DONE
        self._update_stage(job)
        if self._scan_result_repository is not None:
            self._scan_result_repository.save_overall_result(overall_result)
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
