from __future__ import annotations

from src.domain.enums import ErrorType
from src.domain.models import ComparisonError, ObservedField, TemplateSideDefinition


def build_missing_required_errors(
    template_side: TemplateSideDefinition,
    observed_map: dict[str, ObservedField],
) -> list[ComparisonError]:
    errors: list[ComparisonError] = []

    for field in template_side.fields:
        observed = observed_map.get(field.field_name)
        if field.required and (observed is None or not observed.value.strip()):
            errors.append(
                ComparisonError(
                    side=template_side.side,
                    field_name=field.field_name,
                    error_type=ErrorType.MISSING_FIELD,
                    severity=field.priority,
                    expected_value=field.expected_value,
                    actual_value=observed.value if observed else None,
                    bbox=field.bbox,
                    confidence=observed.confidence if observed else None,
                    message="Required field is missing from OCR output.",
                )
            )

    return errors
