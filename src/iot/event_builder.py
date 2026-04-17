from __future__ import annotations

from src.domain.models import OverallInspectionResult


def build_iot_event(result: OverallInspectionResult) -> dict:
    return {
        "scan_job_id": result.scan_job_id,
        "template_id": result.template_id,
        "overall_status": result.overall_status.value if result.overall_status else None,
        "operator_action_required": (
            result.operator_action_required.value
            if result.operator_action_required
            else None
        ),
        "highest_severity": (
            result.highest_severity.value if result.highest_severity else None
        ),
    }
