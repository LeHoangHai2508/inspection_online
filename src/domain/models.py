from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.domain.enums import (
    CompareType,
    ErrorType,
    FieldPriority,
    InspectionSide,
    InspectionStatus,
    OperatorAction,
    RuntimeState,
    TemplateStatus,
)


@dataclass(frozen=True)
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass(frozen=True)
class StoredFile:
    filename: str
    storage_path: str
    media_type: str = "application/octet-stream"


@dataclass(frozen=True)
class OCRBlock:
    text: str
    bbox: BoundingBox
    confidence: float
    line_index: int


@dataclass(frozen=True)
class TemplateFieldDefinition:
    field_name: str
    expected_value: str
    side: InspectionSide
    field_type: str = "text"
    required: bool = True
    compare_type: CompareType = CompareType.EXACT
    priority: FieldPriority = FieldPriority.MAJOR
    bbox: BoundingBox | None = None
    regex_pattern: str | None = None
    fuzzy_threshold: float | None = None
    case_sensitive: bool = False


@dataclass(frozen=True)
class TemplateSideDefinition:
    side: InspectionSide
    raw_text: str = ""
    fields: list[TemplateFieldDefinition] = field(default_factory=list)
    ocr_blocks: list[OCRBlock] = field(default_factory=list)
    source_file: StoredFile | None = None

    def field_names(self) -> set[str]:
        return {field.field_name for field in self.fields}


@dataclass
class TemplateRecord:
    template_id: str
    template_version: str
    template_name: str
    product_code: str
    created_by: str
    status: TemplateStatus
    sides: dict[InspectionSide, TemplateSideDefinition]
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    review_notes: str = ""

    def get_side(self, side: InspectionSide) -> TemplateSideDefinition:
        return self.sides[side]


@dataclass(frozen=True)
class TemplateUploadFile:
    filename: str
    content: bytes
    media_type: str = "application/octet-stream"


@dataclass(frozen=True)
class TemplateUploadRequest:
    template_name: str
    product_code: str
    created_by: str
    side1_file: TemplateUploadFile | None = None
    side2_file: TemplateUploadFile | None = None
    side1_fields: list[TemplateFieldDefinition] = field(default_factory=list)
    side2_fields: list[TemplateFieldDefinition] = field(default_factory=list)
    side1_raw_text: str = ""
    side2_raw_text: str = ""


@dataclass(frozen=True)
class ObservedField:
    field_name: str
    value: str
    confidence: float = 1.0
    bbox: BoundingBox | None = None
    camera_source: str = "fused"


@dataclass(frozen=True)
class CaptureInput:
    filename: str
    content: bytes
    media_type: str = "application/octet-stream"
    camera_id: str = "cam1"


@dataclass(frozen=True)
class SideInspectionInput:
    side: InspectionSide
    observed_fields: list[ObservedField] = field(default_factory=list)
    captures: list[CaptureInput] = field(default_factory=list)
    raw_text: str = ""
    image_quality_ok: bool = True
    image_quality_score: float = 1.0
    # Loại lỗi chất lượng chính xác (LOW_IMAGE_QUALITY / LOW_PRINT_QUALITY / UNCERTAIN_RESULT)
    # None khi chất lượng đạt
    image_quality_error_type: ErrorType | None = None
    # Lý do cụ thể từ quality gate (ví dụ: "Image too dark (brightness=32.1)")
    image_quality_reason: str = ""
    # Localization có tìm thấy tem không
    localization_ok: bool = True
    # Lý do localization fail (bỏ trống khi thành công)
    localization_reason: str = ""
    ocr_blocks: list[OCRBlock] = field(default_factory=list)
    # Panel label detected từ OCR (RECTO/VERSO/UNKNOWN)
    panel_label: str = "UNKNOWN"


@dataclass(frozen=True)
class ComparisonError:
    side: InspectionSide
    field_name: str
    error_type: ErrorType
    severity: FieldPriority
    expected_value: str | None = None
    actual_value: str | None = None
    bbox: BoundingBox | None = None
    confidence: float | None = None
    message: str = ""
    camera_source: str = "fused"


@dataclass
class SideInspectionResult:
    side: InspectionSide
    status: InspectionStatus
    errors: list[ComparisonError] = field(default_factory=list)
    raw_text: str = ""
    processing_time_ms: int = 0
    annotated_assets: dict[str, str] = field(default_factory=dict)
    ocr_blocks: list[OCRBlock] = field(default_factory=list)


@dataclass
class OverallInspectionResult:
    scan_job_id: str
    template_id: str
    side1_result: SideInspectionResult | None = None
    side2_result: SideInspectionResult | None = None
    overall_status: InspectionStatus | None = None
    operator_action_required: OperatorAction | None = None
    highest_severity: FieldPriority | None = None
    publish_to_iot: bool = False


@dataclass
class ScanJob:
    scan_job_id: str
    template_id: str
    line_id: str
    station_id: str
    state: RuntimeState = RuntimeState.WAIT_SIDE1_CAPTURE
    side1_result: SideInspectionResult | None = None
    side2_result: SideInspectionResult | None = None
    overall_result: OverallInspectionResult | None = None


@dataclass(frozen=True)
class TemplateFieldPatch:
    side: InspectionSide
    field_name: str
    expected_value: str
    field_type: str = "text"
    required: bool = True
    compare_type: CompareType = CompareType.EXACT
    priority: FieldPriority = FieldPriority.MAJOR
