from __future__ import annotations

from src.domain.enums import CompareType, FieldPriority, InspectionSide
from src.domain.models import OCRBlock, ObservedField, TemplateFieldDefinition


def extract_candidate_fields(
    side: InspectionSide,
    blocks: list[OCRBlock],
) -> list[TemplateFieldDefinition]:
    return []


def extract_runtime_observed_fields(blocks: list[OCRBlock]) -> list[ObservedField]:
    observed_fields: list[ObservedField] = []

    for block in blocks:
        if ":" not in block.text:
            continue
        field_name, actual_value = block.text.split(":", 1)
        observed_fields.append(
            ObservedField(
                field_name=_slug(field_name),
                value=actual_value.strip(),
                confidence=block.confidence,
                bbox=block.bbox,
            )
        )

    return observed_fields


def _slug(value: str) -> str:
    return "_".join(value.strip().lower().split())
