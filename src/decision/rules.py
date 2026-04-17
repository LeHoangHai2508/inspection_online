from __future__ import annotations

from src.domain.enums import InspectionStatus
from src.domain.error_taxonomy import HARD_FAIL_ERROR_TYPES, UNCERTAIN_ERROR_TYPES
from src.domain.models import ComparisonError


class SideDecisionEngine:
    def decide(self, errors: list[ComparisonError]) -> InspectionStatus:
        if not errors:
            return InspectionStatus.OK

        has_hard_fail = any(error.error_type in HARD_FAIL_ERROR_TYPES for error in errors)
        has_uncertain = any(
            error.error_type in UNCERTAIN_ERROR_TYPES for error in errors
        )

        if has_hard_fail:
            return InspectionStatus.NG
        if has_uncertain:
            return InspectionStatus.UNCERTAIN
        return InspectionStatus.NG


class OverallDecisionEngine:
    def decide(
        self,
        side1_status: InspectionStatus,
        side2_status: InspectionStatus,
    ) -> InspectionStatus:
        if InspectionStatus.NG in {side1_status, side2_status}:
            return InspectionStatus.NG
        if InspectionStatus.UNCERTAIN in {side1_status, side2_status}:
            return InspectionStatus.UNCERTAIN
        return InspectionStatus.OK
