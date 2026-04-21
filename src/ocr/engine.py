from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

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


def _preprocess_for_tesseract(input_path: Path, heavy: bool = True):
    """
    Preprocess ảnh cho Tesseract.
    - side1: nhẹ, giữ nét
    - side2: scale 2x + CLAHE + threshold, không denoise để tránh mất nét chữ nhỏ
    """
    from PIL import Image  # type: ignore

    image = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"Cannot read image for OCR: {input_path}")

    if heavy:
        # Side2: chữ nhỏ, nhiều ngôn ngữ
        # Scale 2x để chữ nhỏ rõ hơn
        image = cv2.resize(
            image,
            None,
            fx=2.0,
            fy=2.0,
            interpolation=cv2.INTER_CUBIC,
        )

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        image = clahe.apply(image)

        # Threshold để tách nét chữ
        _, image = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        # Tắt denoise vì đang làm mất nét nhỏ, dấu chấm, chữ đa ngôn ngữ
        # image = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
    else:
        # Side1: chữ lớn hơn, chỉ cần contrast nhẹ
        clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(8, 8))
        image = clahe.apply(image)

    return Image.fromarray(image)


def _list_installed_tesseract_langs() -> list[str]:
    """
    Lấy danh sách language packs đã cài trong máy từ:
    tesseract --list-langs
    
    Loại bỏ:
    - dòng header
    - dòng rỗng
    - osd / equ vì không phải language pack OCR text thông thường
    """
    if not shutil.which("tesseract"):
        return []

    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return []

    langs: list[str] = []
    for line in result.stdout.splitlines():
        item = line.strip()
        if not item:
            continue
        if ":" in item:
            # bỏ dòng kiểu: "List of available languages in ..."
            continue
        if item in {"osd", "equ"}:
            continue
        langs.append(item)

    # bỏ trùng nhưng giữ thứ tự
    deduped: list[str] = []
    seen = set()
    for lang in langs:
        if lang not in seen:
            seen.add(lang)
            deduped.append(lang)

    return deduped


def _normalize_tesseract_lang_spec(lang: str | None) -> str:
    """
    Nếu config để:
      - all
      - *
    thì tự động dùng toàn bộ language pack đã cài trong Tesseract.
    
    Nếu không lấy được danh sách, fallback về eng.
    """
    raw = (lang or "eng").strip()

    if raw.lower() not in {"all", "*"}:
        return raw

    installed = _list_installed_tesseract_langs()
    if not installed:
        return "eng"

    return "+".join(installed)


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

    def __init__(self, lang: str = "eng", side_langs: dict | None = None) -> None:
        self._lang = _normalize_tesseract_lang_spec(lang)
        self._side_langs = side_langs or {}

    def _lang_for_side(self, side: InspectionSide) -> str:
        """Lấy ngôn ngữ phù hợp cho side, fallback về lang chung"""
        return self._side_langs.get(side.value, self._lang)

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
            # Side2 dùng heavy preprocessing, Side1 dùng light
            heavy = side == InspectionSide.SIDE2
            image = _preprocess_for_tesseract(input_path, heavy=heavy)
            
            # side1 đơn giản hơn -> psm 6
            # side2 nhiều block/ngôn ngữ -> psm 4
            psm = "6" if side == InspectionSide.SIDE1 else "4"
            lang = self._lang_for_side(side)
            
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
                config=f"--oem 3 --psm {psm} -c preserve_interword_spaces=1",
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
            psm = "6" if side == InspectionSide.SIDE1 else "4"
            lang = self._lang_for_side(side)
            
            result = subprocess.run(
                [
                    "tesseract",
                    str(input_path),
                    "stdout",
                    "-l",
                    lang,
                    "--oem",
                    "3",
                    "--psm",
                    psm,
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
        self._side_langs = dict(config.get("side_langs", {}))
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
            return TesseractOCREngine(lang=self._lang, side_langs=self._side_langs)
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
