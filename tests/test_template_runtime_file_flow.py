from __future__ import annotations

import unittest
from pathlib import Path

from src.domain.enums import CompareType, FieldPriority, InspectionSide, InspectionStatus
from src.domain.models import CaptureInput, TemplateFieldPatch, TemplateUploadFile, TemplateUploadRequest
from src.pipeline.orchestrator import InspectionOrchestrator
from src.template_service.repository import InMemoryTemplateRepository
from src.template_service.service import TemplateService


class TemplateRuntimeFileFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template_service = TemplateService(InMemoryTemplateRepository())
        self.orchestrator = InspectionOrchestrator(self.template_service)

    def test_upload_files_build_preview_and_review_state(self) -> None:
        record = self.template_service.create_draft(
            TemplateUploadRequest(
                template_name="demo_template",
                product_code="sku01",
                created_by="tester",
                side1_file=TemplateUploadFile(
                    filename="side1.txt",
                    content=b"product_code: SKU01\ncomposition: 100 COTTON",
                    media_type="text/plain",
                ),
                side2_file=TemplateUploadFile(
                    filename="side2.txt",
                    content=b"country_of_origin: MADE IN VIETNAM",
                    media_type="text/plain",
                ),
            )
        )

        self.assertEqual(record.status.value, "REVIEW_REQUIRED")
        self.assertEqual(len(record.get_side(InspectionSide.SIDE1).ocr_blocks), 2)
        self.assertEqual(
            record.get_side(InspectionSide.SIDE1).fields[0].field_name,
            "product_code",
        )
        preview = self.template_service.get_template_preview(record.template_id)
        self.assertIn("fields_by_side", preview)
        self.assertIn("original_file_paths", preview)
        self.assertEqual(preview["unmapped_blocks"]["side1"], [])

    def test_review_approve_and_runtime_capture_flow(self) -> None:
        draft = self.template_service.create_draft(
            TemplateUploadRequest(
                template_name="demo_template",
                product_code="sku02",
                created_by="tester",
                side1_file=TemplateUploadFile(
                    filename="side1.txt",
                    content=b"product_code: SKU02\ncomposition: 100 COTTON",
                    media_type="text/plain",
                ),
                side2_file=TemplateUploadFile(
                    filename="side2.txt",
                    content=b"country_of_origin: MADE IN VIETNAM",
                    media_type="text/plain",
                ),
            )
        )

        self.template_service.update_fields(
            draft.template_id,
            patches=[
                TemplateFieldPatch(
                    side=InspectionSide.SIDE1,
                    field_name="product_code",
                    expected_value="SKU02",
                    compare_type=CompareType.EXACT,
                    priority=FieldPriority.CRITICAL,
                ),
                TemplateFieldPatch(
                    side=InspectionSide.SIDE1,
                    field_name="composition",
                    expected_value="100 COTTON",
                    compare_type=CompareType.FUZZY,
                    priority=FieldPriority.MAJOR,
                ),
                TemplateFieldPatch(
                    side=InspectionSide.SIDE2,
                    field_name="country_of_origin",
                    expected_value="MADE IN VIETNAM",
                    compare_type=CompareType.EXACT,
                    priority=FieldPriority.CRITICAL,
                ),
            ],
            review_notes="approved field mapping",
        )
        approved = self.template_service.approve_template(
            draft.template_id,
            approved_by="reviewer",
        )

        self.orchestrator.start_scan_job("JOB_FILE_001", approved.template_id)
        side1_result = self.orchestrator.inspect_side1(
            "JOB_FILE_001",
            build_capture_input(
                side=InspectionSide.SIDE1,
                cam1_text="product_code: SKU02\ncomposition: 100 cotton",
                cam2_text="product_code: SKU02\ncomposition: 100 COTTON",
            ),
        )
        self.assertEqual(side1_result.status, InspectionStatus.OK)
        self.assertIn("cam1", side1_result.annotated_assets)
        self.assertTrue(Path(side1_result.annotated_assets["cam1"]).exists())

        self.orchestrator.confirm_side2("JOB_FILE_001")
        overall_result = self.orchestrator.inspect_side2(
            "JOB_FILE_001",
            build_capture_input(
                side=InspectionSide.SIDE2,
                cam1_text="country_of_origin: MADE IN VIETNAM",
                cam2_text="country_of_origin: MADE IN VIETNAM",
            ),
        )

        self.assertEqual(overall_result.overall_status, InspectionStatus.OK)
        self.assertTrue(overall_result.publish_to_iot)
        iot_path = Path("storage/iot_events/JOB_FILE_001.json")
        self.assertTrue(iot_path.exists())

    def test_camera_conflict_returns_uncertain(self) -> None:
        draft = self.template_service.create_draft(
            TemplateUploadRequest(
                template_name="demo_template",
                product_code="sku03",
                created_by="tester",
                side1_file=TemplateUploadFile(
                    filename="side1.txt",
                    content=b"product_code: SKU03\ncomposition: 100 COTTON",
                    media_type="text/plain",
                ),
                side2_file=TemplateUploadFile(
                    filename="side2.txt",
                    content=b"country_of_origin: MADE IN VIETNAM",
                    media_type="text/plain",
                ),
            )
        )
        self.template_service.update_fields(
            draft.template_id,
            patches=[
                TemplateFieldPatch(
                    side=InspectionSide.SIDE1,
                    field_name="product_code",
                    expected_value="SKU03",
                    compare_type=CompareType.EXACT,
                    priority=FieldPriority.CRITICAL,
                ),
                TemplateFieldPatch(
                    side=InspectionSide.SIDE2,
                    field_name="country_of_origin",
                    expected_value="MADE IN VIETNAM",
                    compare_type=CompareType.EXACT,
                    priority=FieldPriority.CRITICAL,
                ),
            ],
        )
        approved = self.template_service.approve_template(
            draft.template_id,
            approved_by="reviewer",
        )
        self.orchestrator.start_scan_job("JOB_FILE_002", approved.template_id)
        side1_result = self.orchestrator.inspect_side1(
            "JOB_FILE_002",
            build_capture_input(
                side=InspectionSide.SIDE1,
                cam1_text="product_code: SKU03",
                cam2_text="product_code: WRONG",
            ),
        )
        self.assertEqual(side1_result.status, InspectionStatus.UNCERTAIN)


def build_capture_input(
    side: InspectionSide,
    cam1_text: str,
    cam2_text: str,
):
    from src.domain.models import SideInspectionInput

    return SideInspectionInput(
        side=side,
        captures=[
            CaptureInput(
                filename=f"{side.value}_cam1.txt",
                content=cam1_text.encode("utf-8"),
                media_type="text/plain",
                camera_id="cam1",
            ),
            CaptureInput(
                filename=f"{side.value}_cam2.txt",
                content=cam2_text.encode("utf-8"),
                media_type="text/plain",
                camera_id="cam2",
            ),
        ],
    )


if __name__ == "__main__":
    unittest.main()
