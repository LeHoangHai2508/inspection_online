from __future__ import annotations

from src.domain.enums import ErrorType, FieldPriority
from src.domain.models import ComparisonError, ObservedField, TemplateSideDefinition


def build_extra_field_errors(
    template_side: TemplateSideDefinition,
    observed_map: dict[str, ObservedField],
) -> list[ComparisonError]:
    """
    This is a lightweight structural check for now.

    Once OCR block order and layout coordinates are available, this module can
    evolve into a true layout engine without touching the orchestration layer.
    """

    template_field_names = template_side.field_names()
    errors: list[ComparisonError] = []

    for field_name, observed in observed_map.items():
        if field_name in template_field_names:
            continue

        errors.append(
            ComparisonError(
                side=template_side.side,
                field_name=field_name,
                error_type=ErrorType.EXTRA_FIELD,
                severity=FieldPriority.MINOR,
                actual_value=observed.value,
                bbox=observed.bbox,
                confidence=observed.confidence,
                message="OCR returned a field that is not defined in template.",
                camera_source=observed.camera_source,
            )
        )

    return errors
