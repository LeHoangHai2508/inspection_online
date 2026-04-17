from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums import InspectionSide
from src.domain.models import (
    CaptureInput,
    ObservedField,
    SideInspectionInput,
    TemplateFieldPatch,
    TemplateUploadFile,
    TemplateUploadRequest,
)


@dataclass(frozen=True)
class TemplateUploadPayload:
    template_name: str
    product_code: str
    created_by: str
    side1_file: TemplateUploadFile
    side2_file: TemplateUploadFile

    def to_command(self) -> TemplateUploadRequest:
        return TemplateUploadRequest(
            template_name=self.template_name,
            product_code=self.product_code,
            created_by=self.created_by,
            side1_file=self.side1_file,
            side2_file=self.side2_file,
        )


@dataclass(frozen=True)
class SideInspectionPayload:
    scan_job_id: str
    template_id: str
    side: InspectionSide
    captures: list[CaptureInput]
    observed_fields: list[ObservedField] | None = None

    def to_command(self) -> SideInspectionInput:
        return SideInspectionInput(
            side=self.side,
            observed_fields=self.observed_fields or [],
            captures=self.captures,
        )


@dataclass(frozen=True)
class TemplateFieldUpdatePayload:
    fields: list[TemplateFieldPatch]
    review_notes: str = ""
