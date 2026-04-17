from __future__ import annotations

from src.domain.enums import ErrorType, FieldPriority

DEFAULT_ERROR_SEVERITY: dict[ErrorType, FieldPriority] = {
    ErrorType.TEXT_MISMATCH: FieldPriority.MAJOR,
    ErrorType.MISSING_FIELD: FieldPriority.MAJOR,
    ErrorType.EXTRA_FIELD: FieldPriority.MINOR,
    ErrorType.LAYOUT_MISMATCH: FieldPriority.MAJOR,
    ErrorType.SYMBOL_MISMATCH: FieldPriority.CRITICAL,
    ErrorType.LOW_PRINT_QUALITY: FieldPriority.MAJOR,
    ErrorType.LOW_IMAGE_QUALITY: FieldPriority.MAJOR,
    ErrorType.WRONG_TEMPLATE: FieldPriority.CRITICAL,
    ErrorType.UNCERTAIN_RESULT: FieldPriority.MAJOR,
}

UNCERTAIN_ERROR_TYPES: set[ErrorType] = {
    ErrorType.LOW_IMAGE_QUALITY,
    ErrorType.LOW_PRINT_QUALITY,
    ErrorType.UNCERTAIN_RESULT,
}

HARD_FAIL_ERROR_TYPES: set[ErrorType] = {
    ErrorType.TEXT_MISMATCH,
    ErrorType.MISSING_FIELD,
    ErrorType.EXTRA_FIELD,
    ErrorType.LAYOUT_MISMATCH,
    ErrorType.SYMBOL_MISMATCH,
    ErrorType.WRONG_TEMPLATE,
}


def default_severity_for_error(error_type: ErrorType) -> FieldPriority:
    return DEFAULT_ERROR_SEVERITY[error_type]
