from __future__ import annotations

import re
from datetime import datetime, timezone

from src.domain.enums import InspectionSide, TemplateStatus
from src.domain.models import (
    TemplateRecord,
    TemplateFieldPatch,
    TemplateSideDefinition,
    TemplateUploadRequest,
    StoredFile,
)
from src.ocr.run_ocr import OCRWorkflow
from src.template_service.repository import TemplateRepository
from src.template_service.validators import validate_template_upload_request
from src.utils.paths import TEMPLATE_STORAGE, ensure_storage_tree, make_side_folder


class TemplateService:
    """Owns the template lifecycle: upload draft -> review -> approve."""

    def __init__(
        self,
        repository: TemplateRepository,
        ocr_workflow: OCRWorkflow | None = None,
    ) -> None:
        self._repository = repository
        self._ocr_workflow = ocr_workflow or OCRWorkflow()
        ensure_storage_tree()

    def create_draft(self, request: TemplateUploadRequest) -> TemplateRecord:
        validate_template_upload_request(request)

        template_id = self._build_template_id(
            template_name=request.template_name,
            product_code=request.product_code,
        )
        template_version = self._repository.next_version(template_id)

        side1_definition = self._build_side_definition(
            template_id=template_id,
            template_version=template_version,
            side=InspectionSide.SIDE1,
            upload_request=request,
        )
        side2_definition = self._build_side_definition(
            template_id=template_id,
            template_version=template_version,
            side=InspectionSide.SIDE2,
            upload_request=request,
        )

        record = TemplateRecord(
            template_id=template_id,
            template_version=template_version,
            template_name=request.template_name.strip(),
            product_code=request.product_code.strip(),
            created_by=request.created_by.strip(),
            status=TemplateStatus.REVIEW_REQUIRED,
            sides={
                InspectionSide.SIDE1: side1_definition,
                InspectionSide.SIDE2: side2_definition,
            },
        )
        return self._repository.save(record)

    def mark_review_required(self, template_id: str) -> TemplateRecord:
        record = self._get_existing_template(template_id)
        record.status = TemplateStatus.REVIEW_REQUIRED
        return self._repository.save(record)

    def approve_template(self, template_id: str, approved_by: str) -> TemplateRecord:
        if not approved_by.strip():
            raise ValueError("approved_by is required.")

        record = self._get_existing_template(template_id)
        if record.status != TemplateStatus.REVIEW_REQUIRED:
            raise ValueError("Template must be in REVIEW_REQUIRED before approve.")
        self._validate_review_ready(record)
        record.status = TemplateStatus.APPROVED
        record.approved_by = approved_by.strip()
        record.approved_at = datetime.now(timezone.utc)
        return self._repository.save(record)

    def reject_template(self, template_id: str) -> TemplateRecord:
        record = self._get_existing_template(template_id)
        record.status = TemplateStatus.REJECTED
        return self._repository.save(record)

    def get_template(self, template_id: str) -> TemplateRecord:
        return self._get_existing_template(template_id)

    def get_template_preview(self, template_id: str) -> dict:
        record = self._get_existing_template(template_id)
        side1 = record.get_side(InspectionSide.SIDE1)
        side2 = record.get_side(InspectionSide.SIDE2)
        return {
            "template_id": record.template_id,
            "template_version": record.template_version,
            "status": record.status.value,
            "side1_raw_text": side1.raw_text,
            "side2_raw_text": side2.raw_text,
            "side1_blocks": [_serialize_block(block) for block in side1.ocr_blocks],
            "side2_blocks": [_serialize_block(block) for block in side2.ocr_blocks],
            "unmapped_blocks": {
                "side1": _unmapped_blocks(side1),
                "side2": _unmapped_blocks(side2),
            },
            "low_confidence_blocks": {
                "side1": _low_confidence_blocks(side1),
                "side2": _low_confidence_blocks(side2),
            },
            "fields_by_side": {
                "side1": [_serialize_field(field) for field in side1.fields],
                "side2": [_serialize_field(field) for field in side2.fields],
            },
            "original_file_paths": {
                "side1": side1.source_file.storage_path if side1.source_file else None,
                "side2": side2.source_file.storage_path if side2.source_file else None,
            },
        }

    def update_fields(
        self,
        template_id: str,
        patches: list[TemplateFieldPatch],
        review_notes: str = "",
    ) -> TemplateRecord:
        record = self._get_existing_template(template_id)

        for side in (InspectionSide.SIDE1, InspectionSide.SIDE2):
            existing_side = record.get_side(side)
            new_fields = [
                field
                for field in [
                    _patch_to_field(patch)
                    for patch in patches
                    if patch.side == side
                ]
            ]
            if new_fields:
                record.sides[side] = TemplateSideDefinition(
                    side=existing_side.side,
                    raw_text=existing_side.raw_text,
                    fields=new_fields,
                    ocr_blocks=existing_side.ocr_blocks,
                    source_file=existing_side.source_file,
                )

        record.review_notes = review_notes.strip()
        record.status = TemplateStatus.REVIEW_REQUIRED
        return self._repository.save(record)

    def get_approved_template(self, template_id: str) -> TemplateRecord:
        record = self._repository.get_approved(template_id)
        if record is None:
            raise LookupError(
                f"Template '{template_id}' does not exist or is not approved."
            )
        return record

    def _get_existing_template(self, template_id: str) -> TemplateRecord:
        record = self._repository.get_latest(template_id)
        if record is None:
            raise LookupError(f"Template '{template_id}' does not exist.")
        return record

    @staticmethod
    def _build_template_id(template_name: str, product_code: str) -> str:
        base = f"{template_name}_{product_code}".upper().strip()
        compact = re.sub(r"[^A-Z0-9]+", "_", base).strip("_")
        return compact or "TEMPLATE"

    def _build_side_definition(
        self,
        template_id: str,
        template_version: str,
        side: InspectionSide,
        upload_request: TemplateUploadRequest,
    ) -> TemplateSideDefinition:
        if side == InspectionSide.SIDE1:
            upload_file = upload_request.side1_file
            provided_fields = upload_request.side1_fields
            provided_raw_text = upload_request.side1_raw_text
        else:
            upload_file = upload_request.side2_file
            provided_fields = upload_request.side2_fields
            provided_raw_text = upload_request.side2_raw_text

        source_file = None
        ocr_blocks = []
        raw_text = provided_raw_text
        fields = list(provided_fields)

        if upload_file is not None:
            source_file = self._persist_upload(
                template_id=template_id,
                template_version=template_version,
                side=side,
                filename=upload_file.filename,
                content=upload_file.content,
                media_type=upload_file.media_type,
            )
            document, extracted_fields = self._ocr_workflow.run_template_ocr(
                side=side,
                file=upload_file,
            )
            raw_text = document.raw_text
            ocr_blocks = document.blocks
            if not fields:
                fields = extracted_fields

        return TemplateSideDefinition(
            side=side,
            raw_text=raw_text,
            fields=fields,
            ocr_blocks=ocr_blocks,
            source_file=source_file,
        )

    def _persist_upload(
        self,
        template_id: str,
        template_version: str,
        side: InspectionSide,
        filename: str,
        content: bytes,
        media_type: str,
    ) -> StoredFile:
        folder = make_side_folder(
            TEMPLATE_STORAGE,
            f"{template_id}_{template_version}",
            side.value,
        )
        path = folder / filename
        path.write_bytes(content)
        # Lưu relative path từ storage root thay vì absolute path
        from src.utils.paths import STORAGE_ROOT
        relative_path = path.relative_to(STORAGE_ROOT)
        return StoredFile(
            filename=filename,
            storage_path=str(relative_path).replace("\\", "/"),  # Normalize path separators
            media_type=media_type,
        )

    def _validate_review_ready(self, record: TemplateRecord) -> None:
        required_business_fields = {
            InspectionSide.SIDE1: {"product_code"},
            InspectionSide.SIDE2: set(),
        }

        for side in (InspectionSide.SIDE1, InspectionSide.SIDE2):
            side_definition = record.get_side(side)
            if not side_definition.fields:
                raise ValueError(f"{side.value} has no reviewed fields.")

            missing_business_fields = (
                required_business_fields[side] - side_definition.field_names()
            )
            if missing_business_fields:
                missing_display = ", ".join(sorted(missing_business_fields))
                raise ValueError(
                    f"{side.value} is missing required business fields: {missing_display}."
                )

            for field in side_definition.fields:
                if field.required and not field.expected_value.strip():
                    raise ValueError(
                        f"{side.value}.{field.field_name} must have expected_value before approve."
                    )


def _patch_to_field(patch: TemplateFieldPatch):
    from src.domain.models import TemplateFieldDefinition

    return TemplateFieldDefinition(
        field_name=patch.field_name,
        expected_value=patch.expected_value,
        side=patch.side,
        field_type=patch.field_type,
        required=patch.required,
        compare_type=patch.compare_type,
        priority=patch.priority,
    )


def _serialize_block(block) -> dict:
    return {
        "text": block.text,
        "confidence": block.confidence,
        "bbox": [block.bbox.x1, block.bbox.y1, block.bbox.x2, block.bbox.y2],
        "line_index": block.line_index,
    }


def _serialize_field(field) -> dict:
    return {
        "field_name": field.field_name,
        "expected_value": field.expected_value,
        "field_type": field.field_type,
        "required": field.required,
        "compare_type": field.compare_type.value,
        "priority": field.priority.value,
    }


def _unmapped_blocks(side_definition: TemplateSideDefinition) -> list[dict]:
    mapped_names = side_definition.field_names()
    unmapped = []
    for block in side_definition.ocr_blocks:
        field_name = _block_field_name(block.text)
        if field_name and field_name not in mapped_names:
            unmapped.append(_serialize_block(block))
    return unmapped


def _low_confidence_blocks(side_definition: TemplateSideDefinition) -> list[dict]:
    return [
        _serialize_block(block)
        for block in side_definition.ocr_blocks
        if block.confidence < 0.75
    ]


def _block_field_name(text: str) -> str | None:
    if ":" not in text:
        return None
    return "_".join(text.split(":", 1)[0].strip().lower().split())
