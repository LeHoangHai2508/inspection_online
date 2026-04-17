from __future__ import annotations

from src.domain.enums import FieldPriority, InspectionStatus, OperatorAction


class OperatorActionDecider:
    def decide(
        self,
        overall_status: InspectionStatus,
        highest_error_severity: FieldPriority | None,
    ) -> OperatorAction:
        if overall_status == InspectionStatus.OK:
            return OperatorAction.CONTINUE
        if overall_status == InspectionStatus.UNCERTAIN:
            return OperatorAction.RECHECK
        if highest_error_severity == FieldPriority.CRITICAL:
            return OperatorAction.STOP_LINE
        return OperatorAction.ALARM
