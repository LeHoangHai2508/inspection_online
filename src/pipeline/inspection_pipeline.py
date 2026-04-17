from __future__ import annotations

from dataclasses import dataclass

from src.annotator.save_evidence import save_evidence_artifacts
from src.compare.aggregate_verify import CompareEngine
from src.decision.rules import SideDecisionEngine
from src.domain.enums import ErrorType, FieldPriority, InspectionStatus
from src.domain.models import CaptureInput, ComparisonError, SideInspectionInput, SideInspectionResult, TemplateRecord
from src.ocr.run_ocr import OCRWorkflow
from src.preprocess.crop import crop_search_window
from src.preprocess.detect_label import localize_label
from src.preprocess.rectify import rectify_label
from src.preprocess.normalize import normalize_capture
from src.preprocess.quality_gate import evaluate_capture_quality
from src.utils.time_utils import elapsed_ms, utc_now


@dataclass
class CameraInspectionEvaluation:
    camera_id: str
    prepared_input: SideInspectionInput
    errors: list[ComparisonError]
    status: InspectionStatus
    # Metadata từ luồng image preparation mới
    localization_method: str = ""
    alignment_method: str = ""
    localization_confidence: float = 0.0


# ── Private helpers ────────────────────────────────────────────────────

def _localization_failed(localized) -> bool:
    """
    Chỉ coi là localization fail với ảnh thật.
    Text fixture trong unit test (media_type=text/*) được phép pass-through.
    """
    if localized.capture.media_type.startswith("text/"):
        return False
    return localized.bbox is None and not localized.corners


def _should_skip_ocr(quality_result) -> bool:
    """
    OCR chỉ bị skip khi ảnh hỏng nặng hoặc không đủ chắc chắn.
    LOW_PRINT_QUALITY vẫn cho OCR tiếp để lấy thêm bằng chứng.
    """
    return quality_result.error_type in {
        ErrorType.LOW_IMAGE_QUALITY,
        ErrorType.UNCERTAIN_RESULT,
    }


def _build_gate_only_input(
    side,
    capture: CaptureInput,
    *,
    image_quality_ok: bool,
    image_quality_score: float,
    image_quality_error_type,
    image_quality_reason: str,
    localization_ok: bool,
    localization_reason: str,
) -> SideInspectionInput:
    """
    Tạo input chỉ mang thông tin gate/localization.
    Dùng cho case chưa được phép OCR tiếp.
    """
    return SideInspectionInput(
        side=side,
        captures=[capture],
        raw_text="",
        observed_fields=[],
        ocr_blocks=[],
        image_quality_ok=image_quality_ok,
        image_quality_score=image_quality_score,
        image_quality_error_type=image_quality_error_type,
        image_quality_reason=image_quality_reason,
        localization_ok=localization_ok,
        localization_reason=localization_reason,
    )


class InspectionPipeline:
    """Runs one inspection side from template lookup to side decision."""

    def __init__(
        self,
        compare_engine: CompareEngine | None = None,
        side_decision_engine: SideDecisionEngine | None = None,
        ocr_workflow: OCRWorkflow | None = None,
    ) -> None:
        self._compare_engine = compare_engine or CompareEngine()
        self._side_decision_engine = side_decision_engine or SideDecisionEngine()
        self._ocr_workflow = ocr_workflow or OCRWorkflow()

    def inspect_side(
        self,
        template: TemplateRecord,
        inspection_input: SideInspectionInput,
        scan_job_id: str | None = None,
    ) -> SideInspectionResult:
        started_at = utc_now()
        template_side = template.get_side(inspection_input.side)

        if inspection_input.captures:
            camera_evaluations = self._evaluate_captures(template, inspection_input)
            status, errors = self._fuse_camera_results(camera_evaluations)
            annotated_assets = self._save_annotations_from_evaluations(
                scan_job_id=scan_job_id,
                side_name=inspection_input.side.value,
                evaluations=camera_evaluations,
            )
            raw_text = "\n\n".join(
                f"[{evaluation.camera_id}]\n{evaluation.prepared_input.raw_text}"
                for evaluation in camera_evaluations
                if evaluation.prepared_input.raw_text
            )
            ocr_blocks = [
                block
                for evaluation in camera_evaluations
                for block in evaluation.prepared_input.ocr_blocks
            ]
            return SideInspectionResult(
                side=inspection_input.side,
                status=status,
                errors=errors,
                raw_text=raw_text,
                processing_time_ms=elapsed_ms(started_at),
                annotated_assets=annotated_assets,
                ocr_blocks=ocr_blocks,
            )

        runtime_input = inspection_input
        errors = self._compare_engine.compare_side(template_side, runtime_input)
        status = self._side_decision_engine.decide(errors)
        annotated_assets = self._save_annotations_from_evaluations(
            scan_job_id=scan_job_id,
            side_name=inspection_input.side.value,
            evaluations=[],
        )
        return SideInspectionResult(
            side=inspection_input.side,
            status=status,
            errors=errors,
            raw_text=runtime_input.raw_text,
            processing_time_ms=elapsed_ms(started_at),
            annotated_assets=annotated_assets,
            ocr_blocks=runtime_input.ocr_blocks,
        )

    def _evaluate_captures(
        self,
        template: TemplateRecord,
        inspection_input: SideInspectionInput,
    ) -> list[CameraInspectionEvaluation]:
        template_side = template.get_side(inspection_input.side)
        evaluations: list[CameraInspectionEvaluation] = []

        for capture in inspection_input.captures:
            # ── Bước 1: Search window ───────────────────────────────────
            search_capture = crop_search_window(capture, side=inspection_input.side)

            # ── Bước 2: Localization ────────────────────────────────
            localized = localize_label(search_capture)

            if _localization_failed(localized):
                # Ảnh thật, không tìm thấy tem — không OCR
                reason = f"Label localization failed (method={localized.method})."
                prepared_input = _build_gate_only_input(
                    side=inspection_input.side,
                    capture=search_capture,
                    image_quality_ok=False,
                    image_quality_score=0.0,
                    image_quality_error_type=ErrorType.UNCERTAIN_RESULT,
                    image_quality_reason="",
                    localization_ok=False,
                    localization_reason=reason,
                )
                errors = self._compare_engine.compare_side(template_side, prepared_input)
                status = self._side_decision_engine.decide(errors)
                evaluations.append(
                    CameraInspectionEvaluation(
                        camera_id=search_capture.camera_id,
                        prepared_input=prepared_input,
                        errors=errors,
                        status=status,
                        localization_method=localized.method,
                        alignment_method="no-alignment",
                        localization_confidence=localized.confidence,
                    )
                )
                continue

            # ── Bước 3–5: Rectify, normalize, quality ─────────────────
            rectified = rectify_label(localized)
            normalized_capture = normalize_capture(rectified.capture)
            quality_result = evaluate_capture_quality(normalized_capture)

            if not quality_result.passed and _should_skip_ocr(quality_result):
                # Ảnh hỏng nặng — không OCR
                prepared_input = _build_gate_only_input(
                    side=inspection_input.side,
                    capture=normalized_capture,
                    image_quality_ok=False,
                    image_quality_score=quality_result.score,
                    image_quality_error_type=quality_result.error_type,
                    image_quality_reason=quality_result.reason,
                    localization_ok=True,
                    localization_reason="",
                )
                errors = self._compare_engine.compare_side(template_side, prepared_input)
                status = self._side_decision_engine.decide(errors)
                evaluations.append(
                    CameraInspectionEvaluation(
                        camera_id=normalized_capture.camera_id,
                        prepared_input=prepared_input,
                        errors=errors,
                        status=status,
                        localization_method=localized.method,
                        alignment_method=rectified.method,
                        localization_confidence=localized.confidence,
                    )
                )
                continue

            # ── Bước 6–8: OCR → compare → decide ─────────────────────
            raw_text, blocks, observed_fields = self._ocr_workflow.run_capture_ocr(
                side=inspection_input.side,
                capture=normalized_capture,
            )
            prepared_input = SideInspectionInput(
                side=inspection_input.side,
                observed_fields=observed_fields,
                captures=[normalized_capture],
                raw_text=raw_text,
                image_quality_ok=quality_result.passed,
                image_quality_score=quality_result.score,
                image_quality_error_type=quality_result.error_type,
                image_quality_reason=quality_result.reason,
                localization_ok=True,
                localization_reason="",
                ocr_blocks=blocks,
            )
            errors = self._compare_engine.compare_side(template_side, prepared_input)
            status = self._side_decision_engine.decide(errors)
            evaluations.append(
                CameraInspectionEvaluation(
                    camera_id=normalized_capture.camera_id,
                    prepared_input=prepared_input,
                    errors=errors,
                    status=status,
                    localization_method=localized.method,
                    alignment_method=rectified.method,
                    localization_confidence=localized.confidence,
                )
            )

        return evaluations

    def _fuse_camera_results(
        self,
        evaluations: list[CameraInspectionEvaluation],
    ) -> tuple[InspectionStatus, list[ComparisonError]]:
        if not evaluations:
            return InspectionStatus.UNCERTAIN, []

        if len(evaluations) == 1:
            evaluation = evaluations[0]
            return evaluation.status, evaluation.errors

        statuses = {evaluation.status for evaluation in evaluations}
        if statuses == {InspectionStatus.OK}:
            return InspectionStatus.OK, []

        if InspectionStatus.OK in statuses and InspectionStatus.NG in statuses:
            return InspectionStatus.UNCERTAIN, self._collect_errors_with_conflict(
                evaluations,
                "Two cameras disagree: one camera is OK while another is NG.",
                evaluations[0].prepared_input.side,
            )

        if InspectionStatus.OK in statuses and statuses <= {
            InspectionStatus.OK,
            InspectionStatus.UNCERTAIN,
        }:
            return InspectionStatus.OK, []

        if statuses == {InspectionStatus.NG}:
            if self._same_error_signature(evaluations):
                primary = min(evaluations, key=lambda item: len(item.errors))
                return InspectionStatus.NG, primary.errors
            return InspectionStatus.UNCERTAIN, self._collect_errors_with_conflict(
                evaluations,
                "Two cameras are NG but the defect signatures are inconsistent.",
                evaluations[0].prepared_input.side,
            )

        if InspectionStatus.UNCERTAIN in statuses and InspectionStatus.NG in statuses:
            return InspectionStatus.UNCERTAIN, self._collect_errors_with_conflict(
                evaluations,
                "One camera is NG while another remains uncertain.",
                evaluations[0].prepared_input.side,
            )

        primary = min(evaluations, key=lambda item: len(item.errors))
        return InspectionStatus.UNCERTAIN, primary.errors or [
            self._camera_conflict_error(
                primary.prepared_input.side,
                "Camera fusion defaulted to UNCERTAIN.",
            )
        ]

    def _save_annotations_from_evaluations(
        self,
        scan_job_id: str | None,
        side_name: str,
        evaluations: list[CameraInspectionEvaluation],
    ) -> dict[str, str]:
        if scan_job_id is None:
            return {}

        annotated_assets: dict[str, str] = {}
        for evaluation in evaluations:
            if not evaluation.prepared_input.captures:
                continue
            artifacts = save_evidence_artifacts(
                scan_job_id=scan_job_id,
                side_name=side_name,
                camera_id=evaluation.camera_id,
                capture=evaluation.prepared_input.captures[0],
                errors=evaluation.errors,
            )
            # Chỉ expose annotated_image để giữ interface cũ (dict[camera_id -> path])
            annotated_assets[evaluation.camera_id] = artifacts["annotated_image"]
        return annotated_assets

    def _collect_errors_with_conflict(
        self,
        evaluations: list[CameraInspectionEvaluation],
        reason: str,
        side,
    ) -> list[ComparisonError]:
        all_errors = [
            error for evaluation in evaluations for error in evaluation.errors
        ]
        all_errors.append(self._camera_conflict_error(side, reason))
        return all_errors

    def _same_error_signature(
        self,
        evaluations: list[CameraInspectionEvaluation],
    ) -> bool:
        signatures = {
            tuple(
                sorted(
                    (
                        error.field_name,
                        error.error_type.value,
                        error.expected_value,
                        error.actual_value,
                    )
                    for error in evaluation.errors
                )
            )
            for evaluation in evaluations
        }
        return len(signatures) == 1

    def _camera_conflict_error(self, side, reason: str) -> ComparisonError:
        return ComparisonError(
            side=side,
            field_name="__camera_fusion__",
            error_type=ErrorType.UNCERTAIN_RESULT,
            severity=FieldPriority.MAJOR,
            message=reason,
            camera_source="fusion",
        )
