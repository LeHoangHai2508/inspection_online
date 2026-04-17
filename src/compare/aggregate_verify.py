from __future__ import annotations

from src.compare.compare_layout import build_extra_field_errors
from src.compare.compare_required_fields import build_missing_required_errors
from src.compare.compare_symbols import compare_symbol_value
from src.compare.compare_text import TextComparator
from src.domain.decision_schema import ComparisonPolicy
from src.domain.enums import CompareType, ErrorType, FieldPriority
from src.domain.error_taxonomy import default_severity_for_error
from src.domain.models import (
    ComparisonError,
    ObservedField,
    SideInspectionInput,
    TemplateFieldDefinition,
    TemplateSideDefinition,
)


class CompareEngine:
    """Compares runtime OCR data against an approved template side."""

    def __init__(self, policy: ComparisonPolicy | None = None) -> None:
        self._policy = policy or ComparisonPolicy()
        self._text_comparator = TextComparator(policy=self._policy)

    def compare_side(
        self,
        template_side: TemplateSideDefinition,
        inspection_input: SideInspectionInput,
    ) -> list[ComparisonError]:
        errors: list[ComparisonError] = []

        # ── 1) Localization fail → không compare field, dừng ngay ──────────
        if not inspection_input.localization_ok:
            return [
                ComparisonError(
                    side=inspection_input.side,
                    field_name="__localization__",
                    error_type=ErrorType.UNCERTAIN_RESULT,
                    severity=FieldPriority.MAJOR,
                    actual_value=inspection_input.localization_reason,
                    message=inspection_input.localization_reason or "Label localization failed.",
                )
            ]

        # ── 2) Quality fail → dùng đúng loại lỗi pipeline đã phân loại ─────
        if not inspection_input.image_quality_ok:
            quality_error_type = (
                inspection_input.image_quality_error_type or ErrorType.LOW_IMAGE_QUALITY
            )
            quality_error = ComparisonError(
                side=inspection_input.side,
                field_name="__image__",
                error_type=quality_error_type,
                severity=default_severity_for_error(quality_error_type),
                actual_value=str(inspection_input.image_quality_score),
                message=inspection_input.image_quality_reason or "Image quality failed the runtime gate.",
            )

            # Ảnh hỏng nặng / không chắc chắn → dừng, không compare text
            if quality_error_type in {
                ErrorType.LOW_IMAGE_QUALITY,
                ErrorType.UNCERTAIN_RESULT,
            }:
                return [quality_error]

            # LOW_PRINT_QUALITY → ghi lỗi nhưng vẫn compare tiếp (OCR có thể còn đọc được)
            errors.append(quality_error)

        # ── 3) Compare bình thường ───────────────────────────────────────────
        observed_map = {
            observed.field_name: observed
            for observed in inspection_input.observed_fields
        }

        errors.extend(build_missing_required_errors(template_side, observed_map))

        for template_field in template_side.fields:
            observed = observed_map.get(template_field.field_name)
            if observed is None or not observed.value.strip():
                continue
            errors.extend(self._compare_field(template_field, observed))

        errors.extend(build_extra_field_errors(template_side, observed_map))
        return errors

    def _compare_field(
        self,
        template_field: TemplateFieldDefinition,
        observed: ObservedField,
    ) -> list[ComparisonError]:
        errors: list[ComparisonError] = []

        if observed.confidence < self._policy.low_confidence_threshold:
            errors.append(
                ComparisonError(
                    side=template_field.side,
                    field_name=template_field.field_name,
                    error_type=ErrorType.UNCERTAIN_RESULT,
                    severity=template_field.priority,
                    expected_value=template_field.expected_value,
                    actual_value=observed.value,
                    bbox=observed.bbox,
                    confidence=observed.confidence,
                    message="OCR confidence is lower than accepted threshold.",
                    camera_source=observed.camera_source,
                )
            )

        if template_field.compare_type == CompareType.SYMBOL_MATCH:
            matched = compare_symbol_value(
                template_field.expected_value,
                observed.value,
            )
            if not matched:
                errors.append(
                    ComparisonError(
                        side=template_field.side,
                        field_name=template_field.field_name,
                        error_type=ErrorType.SYMBOL_MISMATCH,
                        severity=template_field.priority,
                        expected_value=template_field.expected_value,
                        actual_value=observed.value,
                        bbox=observed.bbox,
                        confidence=observed.confidence,
                        message="Symbol value does not match approved template.",
                        camera_source=observed.camera_source,
                    )
                )
            return errors

        comparison = self._text_comparator.compare(template_field, observed.value)
        if comparison.matched:
            return errors

        errors.append(
            ComparisonError(
                side=template_field.side,
                field_name=template_field.field_name,
                error_type=ErrorType.TEXT_MISMATCH,
                severity=template_field.priority,
                expected_value=comparison.expected_value,
                actual_value=comparison.actual_value,
                bbox=observed.bbox,
                confidence=observed.confidence,
                message="Field value does not match approved template.",
                camera_source=observed.camera_source,
            )
        )
        return errors
