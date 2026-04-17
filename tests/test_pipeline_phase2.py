"""
Test suite cho Phase 1 + Phase 2 runtime pipeline.

Kiểm tra 5 hành vi mới theo thứ tự spec:
1. Localization fail thật phải dừng, ra UNCERTAIN (không OCR mù).
2. Text fixture KHÔNG bị fail vì localization (pass-through).
3. LOW_PRINT_QUALITY phải giữ đúng loại lỗi.
4. LOW_IMAGE_QUALITY phải skip OCR hoàn toàn.
5. Evidence phải tạo 3 file artifact (aligned, annotated, json).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.domain.enums import (
    CompareType,
    ErrorType,
    FieldPriority,
    InspectionSide,
    InspectionStatus,
)
from src.domain.models import (
    BoundingBox,
    CaptureInput,
    ComparisonError,
    ObservedField,
    SideInspectionInput,
    TemplateSideDefinition,
    TemplateFieldDefinition,
    TemplateUploadRequest,
)
from src.compare.aggregate_verify import CompareEngine
from src.preprocess.quality_gate import QualityGateResult
from src.preprocess.types import LocalizedLabel, RectifiedCapture
from src.template_service.repository import InMemoryTemplateRepository
from src.template_service.service import TemplateService


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _make_image_capture(camera_id: str = "cam1") -> CaptureInput:
    """Tạo 1×1 pixel PNG giả — đủ để Pillow đọc được."""
    from io import BytesIO
    try:
        from PIL import Image
        buf = BytesIO()
        Image.new("RGB", (1, 1), color=(255, 255, 255)).save(buf, format="PNG")
        return CaptureInput(
            filename="test.png",
            content=buf.getvalue(),
            media_type="image/png",
            camera_id=camera_id,
        )
    except ImportError:
        return CaptureInput(
            filename="test.png",
            content=b"\x89PNG\r\n\x1a\n",
            media_type="image/png",
            camera_id=camera_id,
        )


def _make_text_capture(camera_id: str = "cam1") -> CaptureInput:
    return CaptureInput(
        filename="fixture.txt",
        content=b"product_code: C8-99/L31",
        media_type="text/plain",
        camera_id=camera_id,
    )


def _make_template_side(side: InspectionSide = InspectionSide.SIDE1) -> TemplateSideDefinition:
    return TemplateSideDefinition(
        side=side,
        fields=[
            TemplateFieldDefinition(
                field_name="product_code",
                expected_value="C8-99/L31",
                side=side,
                compare_type=CompareType.EXACT,
                priority=FieldPriority.CRITICAL,
            )
        ],
    )


def _make_upload_request(name: str, product_code: str) -> TemplateUploadRequest:
    """
    Tạo TemplateUploadRequest có đủ cả side1_fields và side2_fields.
    Validator yêu cầu cả hai mặt — không được bỏ bên nào.
    """
    _field = lambda side: TemplateFieldDefinition(
        field_name="product_code",
        expected_value="X",
        side=side,
        compare_type=CompareType.EXACT,
        priority=FieldPriority.MAJOR,
    )
    return TemplateUploadRequest(
        template_name=name,
        product_code=product_code,
        created_by="op",
        side1_fields=[_field(InspectionSide.SIDE1)],
        side2_fields=[_field(InspectionSide.SIDE2)],
    )


def _make_approved_template(template_name: str = "t1", product_code: str = "p1"):
    """
    Dựng template đã approve trong memory.
    Dùng chung để tránh lặp setup dài dòng trong từng test.
    """
    repo = InMemoryTemplateRepository()
    svc = TemplateService(repo)
    req = _make_upload_request(name=template_name, product_code=product_code)
    draft = svc.create_draft(req)
    return svc.approve_template(draft.template_id, "rev")


# ─── Test 1: Localization fail thật → UNCERTAIN, không OCR ───────────────────

class TestLocalizationFail(unittest.TestCase):
    """Nếu localization fail với ảnh thật thì pipeline dừng, không gọi OCR."""

    def _run_with_localize_fail(self, bbox_value):
        """
        Chạy pipeline với localized.bbox được set theo tham số.
        bbox_value=None  → localization fail
        bbox_value=BoundingBox → localization thành công
        """
        from src.pipeline.inspection_pipeline import InspectionPipeline

        template = _make_approved_template("t1", "p1")

        fake_localized = LocalizedLabel(
            capture=_make_image_capture(),
            bbox=bbox_value,
            corners=[] if bbox_value is None else [(0, 0), (1, 0), (1, 1), (0, 1)],
            confidence=0.0 if bbox_value is None else 0.9,
            method="rule-based-contour",
        )

        mock_ocr = MagicMock()
        mock_ocr.run_capture_ocr.return_value = ("", [], [])
        pipeline = InspectionPipeline(ocr_workflow=mock_ocr)

        inspection_input = SideInspectionInput(
            side=InspectionSide.SIDE1,
            captures=[_make_image_capture()],
        )

        with patch("src.pipeline.inspection_pipeline.crop_search_window", side_effect=lambda c, **kw: c):
            with patch("src.pipeline.inspection_pipeline.localize_label", return_value=fake_localized):
                result = pipeline.inspect_side(template, inspection_input)

        return result, mock_ocr

    def test_localization_fail_gives_uncertain_status(self):
        result, _ = self._run_with_localize_fail(bbox_value=None)
        self.assertEqual(result.status, InspectionStatus.UNCERTAIN)

    def test_localization_fail_emits_uncertain_result_error(self):
        result, _ = self._run_with_localize_fail(bbox_value=None)
        error_types = [e.error_type for e in result.errors]
        self.assertIn(ErrorType.UNCERTAIN_RESULT, error_types)

    def test_localization_fail_skips_ocr(self):
        _, mock_ocr = self._run_with_localize_fail(bbox_value=None)
        mock_ocr.run_capture_ocr.assert_not_called()


# ─── Test 2: Text fixture pass-through ───────────────────────────────────────

class TestTextFixturePassThrough(unittest.TestCase):
    """text/plain fixture phải bypass localization check và compare bình thường."""

    def test_localization_ok_flag_allows_compare(self):
        engine = CompareEngine()
        template_side = _make_template_side()
        inspection_input = SideInspectionInput(
            side=InspectionSide.SIDE1,
            observed_fields=[ObservedField("product_code", "C8-99/L31", confidence=0.99)],
            localization_ok=True,
        )
        errors = engine.compare_side(template_side, inspection_input)
        self.assertEqual(errors, [])

    def test_localization_fail_flag_blocks_compare(self):
        """localization_ok=False phải dừng compare field ngay."""
        engine = CompareEngine()
        template_side = _make_template_side()
        inspection_input = SideInspectionInput(
            side=InspectionSide.SIDE1,
            observed_fields=[ObservedField("product_code", "C8-99/L31", confidence=0.99)],
            localization_ok=False,
            localization_reason="no contour found",
        )
        errors = engine.compare_side(template_side, inspection_input)
        # Phải chỉ có 1 lỗi __localization__, không có lỗi field
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].field_name, "__localization__")
        self.assertEqual(errors[0].error_type, ErrorType.UNCERTAIN_RESULT)

    def test_text_fixture_capture_passes_localization_gate(self):
        """Trong pipeline, text fixture không bị block bởi _localization_failed()."""
        from src.pipeline.inspection_pipeline import _localization_failed

        text_capture = _make_text_capture()
        fake_localized = LocalizedLabel(
            capture=text_capture,
            bbox=None,
            corners=[],
            confidence=0.0,
            method="text-fixture",
        )
        # Dù bbox=None, text fixture không được coi là fail
        self.assertFalse(_localization_failed(fake_localized))


# ─── Test 3: LOW_PRINT_QUALITY giữ đúng loại lỗi ────────────────────────────

class TestLowPrintQualityErrorType(unittest.TestCase):
    """CompareEngine phải phát ra LOW_PRINT_QUALITY, không đổi thành LOW_IMAGE_QUALITY."""

    def test_low_print_quality_keeps_correct_error_type(self):
        engine = CompareEngine()
        template_side = _make_template_side()
        inspection_input = SideInspectionInput(
            side=InspectionSide.SIDE1,
            image_quality_ok=False,
            image_quality_score=0.4,
            image_quality_error_type=ErrorType.LOW_PRINT_QUALITY,
            image_quality_reason="Ink faint: contrast=5.2",
            localization_ok=True,
            observed_fields=[ObservedField("product_code", "C8-99/L31", confidence=0.99)],
        )
        errors = engine.compare_side(template_side, inspection_input)

        quality_errors = [e for e in errors if e.field_name == "__image__"]
        self.assertEqual(len(quality_errors), 1)
        self.assertEqual(quality_errors[0].error_type, ErrorType.LOW_PRINT_QUALITY)

    def test_low_print_quality_still_compares_fields(self):
        """LOW_PRINT_QUALITY không dừng compare — vẫn phát TEXT_MISMATCH."""
        engine = CompareEngine()
        template_side = _make_template_side()
        inspection_input = SideInspectionInput(
            side=InspectionSide.SIDE1,
            image_quality_ok=False,
            image_quality_score=0.4,
            image_quality_error_type=ErrorType.LOW_PRINT_QUALITY,
            image_quality_reason="Ink faint",
            localization_ok=True,
            observed_fields=[ObservedField("product_code", "WRONG_CODE", confidence=0.99)],
        )
        errors = engine.compare_side(template_side, inspection_input)
        error_types = {e.error_type for e in errors}
        self.assertIn(ErrorType.LOW_PRINT_QUALITY, error_types)
        self.assertIn(ErrorType.TEXT_MISMATCH, error_types)


# ─── Test 4: LOW_IMAGE_QUALITY phải skip OCR ─────────────────────────────────

class TestLowImageQualitySkipsOcr(unittest.TestCase):
    """Khi quality gate trả LOW_IMAGE_QUALITY, OCR workflow không được gọi."""

    def test_low_image_quality_skips_ocr_workflow(self):
        from src.pipeline.inspection_pipeline import InspectionPipeline

        template = _make_approved_template("t2", "p2")

        bad_quality = QualityGateResult(
            passed=False,
            score=0.1,
            error_type=ErrorType.LOW_IMAGE_QUALITY,
            reason="Image too dark (brightness=12.0). Check lighting.",
        )

        # localized với bbox hợp lệ → không vào nhánh localization fail
        localized_ok = LocalizedLabel(
            capture=_make_image_capture(),
            bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10),
            corners=[(0, 0), (10, 0), (10, 10), (0, 10)],
            confidence=0.9,
            method="rule-based-contour",
        )
        rectified_ok = RectifiedCapture(
            capture=_make_image_capture(),
            alignment_applied=True,
            method="bbox-crop",
        )

        mock_ocr = MagicMock()
        mock_ocr.run_capture_ocr.return_value = ("", [], [])
        pipeline = InspectionPipeline(ocr_workflow=mock_ocr)

        inspection_input = SideInspectionInput(
            side=InspectionSide.SIDE1,
            captures=[_make_image_capture()],
        )

        with patch("src.pipeline.inspection_pipeline.crop_search_window", side_effect=lambda c, **kw: c):
            with patch("src.pipeline.inspection_pipeline.localize_label", return_value=localized_ok):
                with patch("src.pipeline.inspection_pipeline.rectify_label", return_value=rectified_ok):
                    with patch("src.pipeline.inspection_pipeline.normalize_capture", side_effect=lambda c: c):
                        with patch("src.pipeline.inspection_pipeline.evaluate_capture_quality", return_value=bad_quality):
                            result = pipeline.inspect_side(template, inspection_input)

        mock_ocr.run_capture_ocr.assert_not_called()
        self.assertEqual(result.status, InspectionStatus.UNCERTAIN)


# ─── Test 5: Evidence phải tạo 3 file artifact ───────────────────────────────

class TestSaveEvidenceArtifacts(unittest.TestCase):
    """save_evidence_artifacts phải tạo 3 file: aligned, annotated, json."""

    def test_creates_three_artifact_files(self):
        from src.annotator.save_evidence import save_evidence_artifacts

        capture = _make_text_capture()

        # Assert nằm TRONG tempdir context để file vẫn tồn tại khi kiểm tra
        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.annotator.save_evidence.ANNOTATION_STORAGE", Path(tmp)):
                artifacts = save_evidence_artifacts(
                    scan_job_id="JOB_EVD_001",
                    side_name="side1",
                    camera_id="cam1",
                    capture=capture,
                    errors=[],
                )

                self.assertIn("aligned_image", artifacts)
                self.assertIn("annotated_image", artifacts)
                self.assertIn("summary_json", artifacts)

                self.assertTrue(Path(artifacts["aligned_image"]).exists())
                self.assertTrue(Path(artifacts["annotated_image"]).exists())
                self.assertTrue(Path(artifacts["summary_json"]).exists())

    def test_summary_json_contains_errors(self):
        from src.annotator.save_evidence import save_evidence_artifacts

        capture = _make_text_capture()
        error = ComparisonError(
            side=InspectionSide.SIDE1,
            field_name="product_code",
            error_type=ErrorType.TEXT_MISMATCH,
            severity=FieldPriority.CRITICAL,
            expected_value="C8-99/L31",
            actual_value="WRONG",
        )

        # Assert và open() nằm TRONG tempdir context
        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.annotator.save_evidence.ANNOTATION_STORAGE", Path(tmp)):
                artifacts = save_evidence_artifacts(
                    scan_job_id="JOB_EVD_002",
                    side_name="side1",
                    camera_id="cam1",
                    capture=capture,
                    errors=[error],
                )

                with open(artifacts["summary_json"], encoding="utf-8") as f:
                    data = json.load(f)

                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]["field_name"], "product_code")
                self.assertEqual(data[0]["error_type"], "TEXT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
