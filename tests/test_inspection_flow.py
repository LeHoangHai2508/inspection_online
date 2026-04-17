from __future__ import annotations

import unittest

from src.domain.enums import CompareType, FieldPriority, InspectionSide, InspectionStatus
from src.domain.models import ObservedField, SideInspectionInput, TemplateFieldDefinition, TemplateUploadRequest
from src.pipeline.orchestrator import InspectionOrchestrator
from src.template_service.repository import InMemoryTemplateRepository
from src.template_service.service import TemplateService


class InspectionFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        repository = InMemoryTemplateRepository()
        self.template_service = TemplateService(repository)
        self.orchestrator = InspectionOrchestrator(self.template_service)

        upload_request = TemplateUploadRequest(
            template_name="label_a01",
            product_code="p001",
            created_by="operator_01",
            side1_fields=[
                TemplateFieldDefinition(
                    field_name="product_code",
                    expected_value="C8-99/L31",
                    side=InspectionSide.SIDE1,
                    compare_type=CompareType.EXACT,
                    priority=FieldPriority.CRITICAL,
                ),
                TemplateFieldDefinition(
                    field_name="composition",
                    expected_value="100 COTTON",
                    side=InspectionSide.SIDE1,
                    compare_type=CompareType.FUZZY,
                    priority=FieldPriority.MAJOR,
                ),
            ],
            side2_fields=[
                TemplateFieldDefinition(
                    field_name="country_of_origin",
                    expected_value="MADE IN VIETNAM",
                    side=InspectionSide.SIDE2,
                    compare_type=CompareType.EXACT,
                    priority=FieldPriority.CRITICAL,
                )
            ],
        )

        draft = self.template_service.create_draft(upload_request)
        self.template = self.template_service.approve_template(
            draft.template_id,
            approved_by="reviewer_01",
        )

    def test_happy_path_generates_ok_and_continue_action(self) -> None:
        self.orchestrator.start_scan_job("JOB_001", self.template.template_id)

        side1_result = self.orchestrator.inspect_side1(
            "JOB_001",
            build_side_input(
                InspectionSide.SIDE1,
                [
                    ObservedField("product_code", "C8-99/L31", confidence=0.99),
                    ObservedField("composition", "100 cotton", confidence=0.95),
                ],
            ),
        )
        self.assertEqual(side1_result.status, InspectionStatus.OK)

        self.orchestrator.confirm_side2("JOB_001")
        overall_result = self.orchestrator.inspect_side2(
            "JOB_001",
            build_side_input(
                InspectionSide.SIDE2,
                [ObservedField("country_of_origin", "MADE IN VIETNAM")],
            ),
        )

        self.assertEqual(overall_result.overall_status, InspectionStatus.OK)
        self.assertEqual(overall_result.operator_action_required.value, "CONTINUE")

    def test_missing_confirm_blocks_side2(self) -> None:
        self.orchestrator.start_scan_job("JOB_002", self.template.template_id)
        self.orchestrator.inspect_side1(
            "JOB_002",
            build_side_input(
                InspectionSide.SIDE1,
                [ObservedField("product_code", "C8-99/L31", confidence=0.99)],
            ),
        )

        with self.assertRaises(ValueError):
            self.orchestrator.inspect_side2(
                "JOB_002",
                build_side_input(
                    InspectionSide.SIDE2,
                    [ObservedField("country_of_origin", "MADE IN VIETNAM")],
                ),
            )

    def test_critical_mismatch_generates_ng(self) -> None:
        self.orchestrator.start_scan_job("JOB_003", self.template.template_id)
        self.orchestrator.inspect_side1(
            "JOB_003",
            build_side_input(
                InspectionSide.SIDE1,
                [
                    ObservedField("product_code", "WRONG-CODE", confidence=0.99),
                    ObservedField("composition", "100 cotton", confidence=0.95),
                ],
            ),
        )
        self.orchestrator.confirm_side2("JOB_003")

        overall_result = self.orchestrator.inspect_side2(
            "JOB_003",
            build_side_input(
                InspectionSide.SIDE2,
                [ObservedField("country_of_origin", "MADE IN VIETNAM")],
            ),
        )

        self.assertEqual(overall_result.side1_result.status, InspectionStatus.NG)
        self.assertEqual(overall_result.overall_status, InspectionStatus.NG)
        self.assertEqual(overall_result.operator_action_required.value, "STOP_LINE")

    def test_low_confidence_generates_uncertain(self) -> None:
        self.orchestrator.start_scan_job("JOB_004", self.template.template_id)
        side1_result = self.orchestrator.inspect_side1(
            "JOB_004",
            build_side_input(
                InspectionSide.SIDE1,
                [
                    ObservedField("product_code", "C8-99/L31", confidence=0.60),
                    ObservedField("composition", "100 cotton", confidence=0.95),
                ],
            ),
        )

        self.assertEqual(side1_result.status, InspectionStatus.UNCERTAIN)


def build_side_input(
    side: InspectionSide,
    observed_fields: list[ObservedField],
) -> SideInspectionInput:
    return SideInspectionInput(side=side, observed_fields=observed_fields)


if __name__ == "__main__":
    unittest.main()
