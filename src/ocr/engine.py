from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Set environment variables BEFORE any paddle imports
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from src.domain.enums import InspectionSide
from src.domain.models import OCRBlock, TemplateUploadFile
from src.ocr.parser import (
    parse_paddle_output,
    parse_tesseract_data,
    parse_text_to_blocks,
    render_blocks_to_text,
)
from src.utils.config_loader import load_yaml_config


@dataclass(frozen=True)
class OCRDocument:
    side: InspectionSide
    raw_text: str
    blocks: list[OCRBlock]
    engine_name: str


class BaseOCREngine:
    engine_name = "base"

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        raise NotImplementedError


class MockOCREngine(BaseOCREngine):
    engine_name = "mock"

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        raw_text = self._decode_content(
            content=file.content,
            filename=file.filename,
            media_type=file.media_type,
        )
        blocks = parse_text_to_blocks(raw_text)
        return OCRDocument(
            side=side,
            raw_text=raw_text,
            blocks=blocks,
            engine_name=self.engine_name,
        )

    @staticmethod
    def _decode_content(content: bytes, filename: str, media_type: str | None) -> str:
        suffix = Path(filename).suffix.lower()
        binary_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".pdf"}

        if media_type and (media_type.startswith("image/") or media_type == "application/pdf"):
            raise RuntimeError(
                f"Mock OCR cannot decode binary image/pdf file: {filename}. "
                "Use paddleocr or tesseract, or upload plain text fixture only."
            )

        if suffix in binary_suffixes:
            raise RuntimeError(
                f"Mock OCR cannot decode binary image/pdf file: {filename}. "
                "Use paddleocr or tesseract, or upload plain text fixture only."
            )

        if not content:
            return f"EMPTY_FILE:{filename}"

        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="ignore") or f"BINARY_FILE:{filename}"


class PaddleOCREngine(BaseOCREngine):
    engine_name = "paddleocr"

    def __init__(self, lang: str = "en", use_angle_cls: bool = True) -> None:
        if importlib.util.find_spec("paddleocr") is None:
            raise RuntimeError("paddleocr is not installed.")
        
        from paddleocr import PaddleOCR  # type: ignore

        self._ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        with _materialize_input(file) as input_path:
            result = self._ocr.ocr(str(input_path))
        blocks = parse_paddle_output(result)
        return OCRDocument(
            side=side,
            raw_text=render_blocks_to_text(blocks),
            blocks=blocks,
            engine_name=self.engine_name,
        )


class TesseractOCREngine(BaseOCREngine):
    engine_name = "tesseract"

    def __init__(self, lang: str = "eng") -> None:
        self._lang = lang

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        if importlib.util.find_spec("pytesseract") and importlib.util.find_spec("PIL"):
            return self._run_with_pytesseract(side, file)
        if shutil.which("tesseract"):
            return self._run_with_cli(side, file)
        raise RuntimeError("Neither pytesseract nor tesseract CLI is available.")

    def _run_with_pytesseract(
        self,
        side: InspectionSide,
        file: TemplateUploadFile,
    ) -> OCRDocument:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        with _materialize_input(file) as input_path:
            # Preprocess đơn giản: grayscale + upscale 2x
            image = Image.open(input_path).convert("L")  # Grayscale
            image = image.resize((image.width * 2, image.height * 2))  # Upscale 2x
            
            data = pytesseract.image_to_data(
                image,
                lang=self._lang,
                output_type=pytesseract.Output.DICT,
                config="--oem 3 --psm 6"  # OEM 3: default, PSM 6: uniform block
            )
        blocks = parse_tesseract_data(data)
        return OCRDocument(
            side=side,
            raw_text=render_blocks_to_text(blocks),
            blocks=blocks,
            engine_name=self.engine_name,
        )

    def _run_with_cli(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        with _materialize_input(file) as input_path:
            result = subprocess.run(
                [
                    "tesseract",
                    str(input_path),
                    "stdout",
                    "-l",
                    self._lang,
                    "--oem",
                    "3",
                    "--psm",
                    "6",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        raw_text = result.stdout.strip()
        blocks = parse_text_to_blocks(raw_text, confidence=0.85)
        return OCRDocument(
            side=side,
            raw_text=raw_text,
            blocks=blocks,
            engine_name=self.engine_name,
        )


class AutoOCREngine(BaseOCREngine):
    """Selects the best available OCR backend at runtime.

    When ``strict_real_ocr=True`` (set in configs/ocr.yaml or passed directly),
    the engine will raise ``RuntimeError`` instead of falling back to the mock
    backend.  Use this in production to avoid silently running on fake data.
    """

    engine_name = "auto"

    def __init__(
        self,
        preferred_engine: str | None = None,
        strict_real_ocr: bool | None = None,
    ) -> None:
        config = load_yaml_config(
            "configs/ocr.yaml",
            default={
                "engine": "auto",
                "lang": "en",
                "use_angle_cls": True,
                "strict_real_ocr": False,
            },
        )
        self._preferred_engine = preferred_engine or str(config.get("engine", "auto"))
        self._lang = str(config.get("lang", "en"))
        self._use_angle_cls = bool(config.get("use_angle_cls", True))
        # Explicit argument wins over config file
        if strict_real_ocr is not None:
            self._strict = strict_real_ocr
        else:
            self._strict = bool(config.get("strict_real_ocr", False))

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        last_error: Exception | None = None

        for engine_name in self._resolve_engine_order():
            if engine_name == "mock" and self._strict:
                # In strict mode we never silently fall back to mock
                break
            try:
                return self._build_engine(engine_name).run(side=side, file=file)
            except Exception as exc:  # pragma: no cover - provider selection path
                last_error = exc
                continue

        if self._strict:
            detail = f": {last_error}" if last_error else ""
            raise RuntimeError(
                f"strict_real_ocr=True but no real OCR backend is available{detail}. "
                "Install paddleocr or tesseract, or set strict_real_ocr=false in configs/ocr.yaml."
            )

        if last_error is not None:
            raise RuntimeError(
                f"Unable to run OCR with any provider: {last_error}"
            ) from last_error
        return MockOCREngine().run(side=side, file=file)

    def _resolve_engine_order(self) -> list[str]:
        if self._preferred_engine == "auto":
            return ["paddleocr", "tesseract", "mock"]
        return [self._preferred_engine, "mock"]

    def _build_engine(self, engine_name: str) -> BaseOCREngine:
        if engine_name == "paddleocr":
            return PaddleOCREngine(lang=self._lang, use_angle_cls=self._use_angle_cls)
        if engine_name == "tesseract":
            return TesseractOCREngine(lang=self._lang)
        return MockOCREngine()
        return MockOCREngine()


class _materialize_input:
    def __init__(self, file: TemplateUploadFile) -> None:
        self._file = file
        self._path: Path | None = None

    def __enter__(self) -> Path:
        suffix = Path(self._file.filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(self._file.content)
            self._path = Path(handle.name)
        return self._path

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._path and self._path.exists():
            self._path.unlink(missing_ok=True)
