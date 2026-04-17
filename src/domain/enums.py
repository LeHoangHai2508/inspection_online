from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Compatibility helper for Python versions without enum.StrEnum."""


class TemplateStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class InspectionSide(StrEnum):
    SIDE1 = "side1"
    SIDE2 = "side2"


class CompareType(StrEnum):
    EXACT = "exact"
    REGEX = "regex"
    FUZZY = "fuzzy"
    SYMBOL_MATCH = "symbol_match"


class FieldPriority(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class InspectionStatus(StrEnum):
    OK = "OK"
    NG = "NG"
    UNCERTAIN = "UNCERTAIN"


class RuntimeState(StrEnum):
    WAIT_SIDE1_CAPTURE = "WAIT_SIDE1_CAPTURE"
    SIDE1_PROCESSING = "SIDE1_PROCESSING"
    SIDE1_DONE_WAIT_CONFIRM = "SIDE1_DONE_WAIT_CONFIRM"
    WAIT_SIDE2_CAPTURE = "WAIT_SIDE2_CAPTURE"
    SIDE2_PROCESSING = "SIDE2_PROCESSING"
    OVERALL_DONE = "OVERALL_DONE"


class OperatorAction(StrEnum):
    CONTINUE = "CONTINUE"
    ALARM = "ALARM"
    STOP_LINE = "STOP_LINE"
    RECHECK = "RECHECK"


class ErrorType(StrEnum):
    TEXT_MISMATCH = "TEXT_MISMATCH"
    MISSING_FIELD = "MISSING_FIELD"
    EXTRA_FIELD = "EXTRA_FIELD"
    LAYOUT_MISMATCH = "LAYOUT_MISMATCH"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    LOW_PRINT_QUALITY = "LOW_PRINT_QUALITY"
    LOW_IMAGE_QUALITY = "LOW_IMAGE_QUALITY"
    WRONG_TEMPLATE = "WRONG_TEMPLATE"
    UNCERTAIN_RESULT = "UNCERTAIN_RESULT"
