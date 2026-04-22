from __future__ import annotations

from src.domain.enums import InspectionSide
from src.domain.models import CaptureInput, ObservedField, TemplateUploadFile
from src.ocr.engine import AutoOCREngine, OCRDocument
from src.ocr.postprocess import (
    extract_candidate_fields,
    extract_runtime_observed_fields,
)
from src.symbol.run_symbol import SymbolWorkflow


class OCRWorkflow:
    def __init__(
        self,
        engine: AutoOCREngine | None = None,
        symbol_workflow: SymbolWorkflow | None = None,
    ) -> None:
        self._engine = engine or AutoOCREngine()
        self._symbol_workflow = symbol_workflow or SymbolWorkflow()

    def run_template_ocr(
        self,
        side: InspectionSide,
        file: TemplateUploadFile,
        ocr_languages: list[str] | None = None,  # ADD THIS PARAMETER
    ) -> tuple[OCRDocument, list]:
        document = self._engine.run(
            side=side,
            file=file,
            ocr_languages=ocr_languages,  # PASS TO ENGINE
        )
        return document, extract_candidate_fields(side=side, blocks=document.blocks)

    def run_capture_ocr(
        self,
        side: InspectionSide,
        capture: CaptureInput,
    ) -> tuple[str, list, list[ObservedField]]:
        document = self._engine.run(
            side=side,
            file=TemplateUploadFile(
                filename=capture.filename,
                content=capture.content,
                media_type=capture.media_type,
            ),
        )

        text_fields = extract_runtime_observed_fields(document.blocks)
        text_fields = [
            ObservedField(
                field_name=field.field_name,
                value=field.value,
                confidence=field.confidence,
                bbox=field.bbox,
                camera_source=capture.camera_id,
            )
            for field in text_fields
        ]

        symbol_fields = self._symbol_workflow.run_capture_symbol(capture)

        observed_fields = text_fields + symbol_fields
        return document.raw_text, document.blocks, observed_fields

    def run_runtime_ocr(
        self,
        side: InspectionSide,
        captures: list[CaptureInput],
    ) -> tuple[str, list, list[ObservedField]]:
        raw_text_parts: list[str] = []
        all_blocks = []
        all_fields: list[ObservedField] = []

        for capture in captures:
            raw_text, blocks, observed_fields = self.run_capture_ocr(side, capture)
            raw_text_parts.append(raw_text)
            all_blocks.extend(blocks)
            all_fields.extend(observed_fields)

        return "\n".join(part for part in raw_text_parts if part), all_blocks, all_fields
