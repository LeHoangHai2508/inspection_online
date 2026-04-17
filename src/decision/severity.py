from __future__ import annotations

from src.domain.enums import FieldPriority
from src.domain.models import ComparisonError

SEVERITY_ORDER: dict[FieldPriority, int] = {
    FieldPriority.MINOR: 1,
    FieldPriority.MAJOR: 2,
    FieldPriority.CRITICAL: 3,
}


def highest_severity(errors: list[ComparisonError]) -> FieldPriority | None:
    if not errors:
        return None
    return max(errors, key=lambda error: SEVERITY_ORDER[error.severity]).severity
