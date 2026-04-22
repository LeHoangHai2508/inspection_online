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
from PIL import Image

# Set environment variables BEFORE any paddle imports
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from src.domain.enums import InspectionSide
from src.domain.models import BoundingBox, OCRBlock, TemplateUploadFile
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
    - side1: resize nhẹ + CLAHE để giữ chữ nhỏ ở cuối nhãn
    - side2: scale 2x + CLAHE + threshold
    """
    from PIL import Image  # type: ignore

    image = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"Cannot read image for OCR: {input_path}")

    if heavy:
        # Side2: chữ nhỏ, nhiều ngôn ngữ
        image = cv2.resize(
            image,
            None,
            fx=2.0,
            fy=2.0,
            interpolation=cv2.INTER_CUBIC,
        )

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        image = clahe.apply(image)

        # Bỏ threshold cho side2 để giữ nét chữ Trung nhỏ ở cuối nhãn.
        # Threshold toàn cục đang làm dính nét/gãy nét với CJK nhỏ.
        # _, image = cv2.threshold(
        #     image,
        #     0,
        #     255,
        #     cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        # )

        # Tắt denoise để không mất nét nhỏ
        # image = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
    else:
        # Side1: thêm resize nhẹ để giữ nét phần cuối nhãn
        image = cv2.resize(
            image,
            None,
            fx=1.6,
            fy=1.6,
            interpolation=cv2.INTER_CUBIC,
        )

        clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8))
        image = clahe.apply(image)

    return Image.fromarray(image)


def _crop_footer_for_side(side: InspectionSide, image: "Image.Image") -> "Image.Image":
    """
    Cắt bỏ footer nhiễu trước OCR.
    - side1: không cắt footer vì phần cuối còn text composition quan trọng
    - side2: cắt khoảng 10% đáy ảnh để bỏ VERSO 2 và các vạch tím
    """
    from PIL import Image  # type: ignore
    
    width, height = image.size

    if side == InspectionSide.SIDE2:
        crop_bottom = int(height * 0.90)
        return image.crop((0, 0, width, crop_bottom))

    return image


def _ocr_image_to_blocks(image: "Image.Image", lang: str, psm: str) -> list[OCRBlock]:
    """
    OCR một ảnh PIL và trả về OCR blocks bằng đúng parser hiện tại.
    Hàm này dùng lại cho pass chính và các pass phụ.
    """
    import pytesseract  # type: ignore

    data = pytesseract.image_to_data(
        image,
        lang=lang,
        output_type=pytesseract.Output.DICT,
        config=f"--oem 3 --psm {psm} -c preserve_interword_spaces=1",
    )
    return parse_tesseract_data(data)


def _offset_blocks(blocks: list[OCRBlock], dx: int = 0, dy: int = 0) -> list[OCRBlock]:
    """Offset bbox của blocks theo dx, dy"""
    adjusted: list[OCRBlock] = []

    for block in blocks:
        adjusted.append(
            OCRBlock(
                text=block.text,
                bbox=BoundingBox(
                    block.bbox.x1 + dx,
                    block.bbox.y1 + dy,
                    block.bbox.x2 + dx,
                    block.bbox.y2 + dy,
                ),
                confidence=block.confidence,
                line_index=block.line_index,
            )
        )

    return adjusted


def _contains_arabic(text: str) -> bool:
    """Kiểm tra text có chứa ký tự Arabic"""
    import re
    return bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text or ""))


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


def _detect_gpu_available() -> bool:
    """
    Tự động detect GPU có available không.
    Kiểm tra cả PyTorch (EasyOCR) và TensorFlow (KerasOCR).
    """
    pytorch_gpu = False
    tensorflow_gpu = False
    
    # Check PyTorch CUDA
    try:
        import torch
        pytorch_gpu = torch.cuda.is_available()
    except Exception:
        pass
    
    # Check TensorFlow GPU
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        tensorflow_gpu = len(gpus) > 0
    except Exception:
        pass
    
    # Cả 2 phải có GPU mới return True
    has_gpu = pytorch_gpu and tensorflow_gpu
    
    if has_gpu:
        print(f"[GPU] Auto-detected: PyTorch CUDA={pytorch_gpu}, TensorFlow GPU={tensorflow_gpu} → Using GPU")
    else:
        print(f"[GPU] Auto-detected: PyTorch CUDA={pytorch_gpu}, TensorFlow GPU={tensorflow_gpu} → Using CPU")
    
    return has_gpu


def _resolve_gpu_setting(gpu_config: str | bool) -> bool:
    """
    Resolve GPU setting từ config.
    
    Args:
        gpu_config: "auto", "true", "false", True, False
    
    Returns:
        bool: True nếu dùng GPU, False nếu dùng CPU
    """
    if isinstance(gpu_config, bool):
        return gpu_config
    
    gpu_str = str(gpu_config).lower().strip()
    
    if gpu_str == "auto":
        return _detect_gpu_available()
    
    if gpu_str in {"true", "1", "yes", "on"}:
        return True
    
    return False


def _preprocess_for_ensemble(input_path: Path, side: InspectionSide) -> np.ndarray:
    """
    Preprocess nhẹ cho EasyOCR primary.
    Không threshold mạnh để tránh giết nét Arabic/CJK nhỏ.
    """
    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Cannot read image for OCR: {input_path}")

    # Crop footer noise cho side2 để tránh dính RECTO/VERSO
    if side == InspectionSide.SIDE2:
        h, w = image.shape[:2]
        crop_bottom = int(h * 0.90)
        image = image[:crop_bottom, :]

    # Resize nhẹ để giữ chi tiết
    scale = 1.6 if side == InspectionSide.SIDE1 else 2.0
    image = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )

    return image


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


class EasyOCREngine(BaseOCREngine):
    engine_name = "easyocr"

    def __init__(self, langs: list[str], gpu: bool = True) -> None:
        if importlib.util.find_spec("easyocr") is None:
            raise RuntimeError("easyocr is not installed.")

        import easyocr  # type: ignore
        
        print(f"[EasyOCR] Initializing with GPU={gpu}, langs={langs}")
        self._reader = easyocr.Reader(langs, gpu=gpu)
        self._gpu = gpu

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        print(f"[EasyOCR] Running OCR on {side.value} (GPU={self._gpu})")
        
        with _materialize_input(file) as input_path:
            image = _preprocess_for_ensemble(input_path, side)
            result = self._reader.readtext(image, detail=1)

        blocks: list[OCRBlock] = []

        for idx, item in enumerate(result, start=1):
            # EasyOCR: [bbox_points, text, confidence]
            bbox_points, text, confidence = item
            xs = [int(point[0]) for point in bbox_points]
            ys = [int(point[1]) for point in bbox_points]

            blocks.append(
                OCRBlock(
                    text=str(text).strip(),
                    bbox=BoundingBox(min(xs), min(ys), max(xs), max(ys)),
                    confidence=float(confidence),
                    line_index=idx,
                )
            )

        print(f"[EasyOCR] Found {len(blocks)} blocks")
        
        return OCRDocument(
            side=side,
            raw_text=render_blocks_to_text(blocks),
            blocks=blocks,
            engine_name=self.engine_name,
        )


class KerasOCRVerifier:
    """
    Verifier cho hard blocks.
    Không dùng cho toàn ảnh.
    """
    def __init__(self) -> None:
        if importlib.util.find_spec("keras_ocr") is None:
            raise RuntimeError("keras_ocr is not installed.")

        import keras_ocr  # type: ignore
        self._pipeline = keras_ocr.pipeline.Pipeline()

    def verify(self, crop_bgr: np.ndarray) -> tuple[str, float]:
        """
        Trả về:
        - text do KerasOCR đọc
        - confidence heuristic
        """
        import keras_ocr  # type: ignore

        # keras_ocr dùng RGB
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)

        predictions = self._pipeline.recognize([crop_rgb])[0]

        if not predictions:
            return "", 0.0

        # predictions: list[(text, box)]
        texts = []
        for pred in predictions:
            text = pred[0]
            if text:
                texts.append(text.strip())

        merged = " ".join(texts).strip()
        if not merged:
            return "", 0.0

        # KerasOCR không trả confidence chuẩn như EasyOCR,
        # nên dùng heuristic đơn giản:
        confidence = 0.75
        return merged, confidence


def _is_hard_block(
    side: InspectionSide,
    block: OCRBlock,
    image_height: int,
    min_confidence_to_skip: float,
    min_block_width: int,
    min_block_height: int,
) -> bool:
    width = block.bbox.x2 - block.bbox.x1
    height = block.bbox.y2 - block.bbox.y1

    if width < min_block_width or height < min_block_height:
        return False

    # block confidence thấp
    if block.confidence < min_confidence_to_skip:
        return True

    # side1: block có Arabic
    if side == InspectionSide.SIDE1:
        if any("\u0600" <= ch <= "\u06FF" for ch in block.text):
            return True

    # side2: vùng cuối ảnh dễ lỗi Chinese/CJK
    if side == InspectionSide.SIDE2:
        if block.bbox.y1 >= int(image_height * 0.62):
            return True

    return False


def _crop_block(image: np.ndarray, block: OCRBlock, pad: int = 4) -> np.ndarray:
    h, w = image.shape[:2]

    x1 = max(0, block.bbox.x1 - pad)
    y1 = max(0, block.bbox.y1 - pad)
    x2 = min(w, block.bbox.x2 + pad)
    y2 = min(h, block.bbox.y2 + pad)

    return image[y1:y2, x1:x2]


def _should_replace_block(old_block: OCRBlock, new_text: str, new_confidence: float) -> bool:
    if not new_text.strip():
        return False

    old_len = len(old_block.text.strip())
    new_len = len(new_text.strip())

    # verifier phải ít nhất không tệ hơn hẳn
    if new_confidence < old_block.confidence and new_len < old_len:
        return False

    # nếu old confidence thấp, ưu tiên text mới dài và đầy hơn
    if old_block.confidence < 0.75 and new_len >= old_len:
        return True

    # nếu text cũ quá ngắn hoặc rác
    if old_len <= 2 and new_len > old_len:
        return True

    return False


class EnsembleOCREngine(BaseOCREngine):
    engine_name = "ensemble"

    def __init__(
        self,
        easyocr_langs: list[str],
        verifier_enabled: bool = True,
        min_confidence_to_skip: float = 0.82,
        min_block_width: int = 20,
        min_block_height: int = 12,
        max_blocks_per_image: int = 12,
        gpu: bool = True,
    ) -> None:
        print(f"[Ensemble] Initializing with GPU={gpu}, verifier={verifier_enabled}")
        
        self._primary = EasyOCREngine(langs=easyocr_langs, gpu=gpu)
        self._verifier = KerasOCRVerifier() if verifier_enabled else None
        self._gpu = gpu

        self._min_confidence_to_skip = min_confidence_to_skip
        self._min_block_width = min_block_width
        self._min_block_height = min_block_height
        self._max_blocks_per_image = max_blocks_per_image

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        print(f"[Ensemble] Running on {side.value} (GPU={self._gpu})")
        
        with _materialize_input(file) as input_path:
            image = _preprocess_for_ensemble(input_path, side)

        primary_result = self._primary.run(side=side, file=file)

        if self._verifier is None:
            print(f"[Ensemble] Verifier disabled, returning primary result")
            return primary_result

        image_height = image.shape[0]

        hard_blocks: list[OCRBlock] = [
            block
            for block in primary_result.blocks
            if _is_hard_block(
                side=side,
                block=block,
                image_height=image_height,
                min_confidence_to_skip=self._min_confidence_to_skip,
                min_block_width=self._min_block_width,
                min_block_height=self._min_block_height,
            )
        ]

        hard_blocks = hard_blocks[: self._max_blocks_per_image]
        
        print(f"[Ensemble] Found {len(hard_blocks)} hard blocks to verify")

        replaced_map: dict[tuple[int, int, int, int], OCRBlock] = {}

        for idx, block in enumerate(hard_blocks, start=1):
            crop = _crop_block(image, block)
            if crop.size == 0:
                continue

            new_text, new_conf = self._verifier.verify(crop)

            if _should_replace_block(block, new_text, new_conf):
                print(f"[Ensemble] Block {idx}/{len(hard_blocks)}: '{block.text[:20]}...' → '{new_text[:20]}...' (conf {block.confidence:.2f} → {new_conf:.2f})")
                replaced_map[(block.bbox.x1, block.bbox.y1, block.bbox.x2, block.bbox.y2)] = OCRBlock(
                    text=new_text,
                    bbox=block.bbox,
                    confidence=max(block.confidence, new_conf),
                    line_index=block.line_index,
                )

        final_blocks: list[OCRBlock] = []
        for block in primary_result.blocks:
            key = (block.bbox.x1, block.bbox.y1, block.bbox.x2, block.bbox.y2)
            final_blocks.append(replaced_map.get(key, block))

        print(f"[Ensemble] Replaced {len(replaced_map)} blocks")

        return OCRDocument(
            side=side,
            raw_text=render_blocks_to_text(final_blocks),
            blocks=final_blocks,
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

        print(f"[OCR] backend=pytesseract, side={side.value}")

        with _materialize_input(file) as input_path:
            # Side2 dùng heavy preprocessing, Side1 dùng light
            heavy = side == InspectionSide.SIDE2
            image = _preprocess_for_tesseract(input_path, heavy=heavy)
            
            lang = self._lang_for_side(side)
            
            # Side2: 2-pass OCR để xử lý phần cuối tốt hơn
            if side == InspectionSide.SIDE2:
                print(f"[OCR] side2: 2-pass mode")
                
                # Pass 1: OCR toàn ảnh
                print(f"[OCR] pass1: full image, psm=11, lang={lang}")
                data1 = pytesseract.image_to_data(
                    image,
                    lang=lang,
                    output_type=pytesseract.Output.DICT,
                    config=f"--oem 3 --psm 11 -c preserve_interword_spaces=1",
                )
                main_blocks = parse_tesseract_data(data1)
                
                # Pass 2: Crop 35% cuối, OCR lại với config tối ưu cho CJK
                width, height = image.size
                crop_top = int(height * 0.65)
                tail_image = image.crop((0, crop_top, width, height))
                
                # Lang cho phần cuối: ưu tiên CJK
                tail_lang = "chi_sim+chi_tra+jpn+kor+eng+rus+tha"
                print(f"[OCR] pass2: bottom 35%, psm=11, lang={tail_lang}")
                
                data2 = pytesseract.image_to_data(
                    tail_image,
                    lang=tail_lang,
                    output_type=pytesseract.Output.DICT,
                    config=f"--oem 3 --psm 11 -c preserve_interword_spaces=1",
                )
                tail_blocks = parse_tesseract_data(data2)
                
                # Offset bbox của tail_blocks về hệ tọa độ ảnh gốc
                adjusted_tail_blocks = []
                for block in tail_blocks:
                    adjusted_tail_blocks.append(
                        OCRBlock(
                            text=block.text,
                            bbox=BoundingBox(
                                block.bbox.x1,
                                block.bbox.y1 + crop_top,
                                block.bbox.x2,
                                block.bbox.y2 + crop_top,
                            ),
                            confidence=block.confidence,
                            line_index=block.line_index,
                        )
                    )
                
                # Merge: bỏ main_blocks ở vùng cuối, thay bằng tail_blocks
                merged_blocks = [
                    block for block in main_blocks if block.bbox.y2 < crop_top
                ] + adjusted_tail_blocks
                
                # Re-sort và tạo lại blocks với line_index mới
                merged_blocks = sorted(merged_blocks, key=lambda b: (b.bbox.y1, b.bbox.x1))
                
                # Tạo lại blocks với line_index đúng (vì frozen dataclass)
                final_blocks = []
                for i, block in enumerate(merged_blocks, start=1):
                    final_blocks.append(
                        OCRBlock(
                            text=block.text,
                            bbox=block.bbox,
                            confidence=block.confidence,
                            line_index=i,
                        )
                    )
                
                print(f"[OCR] merged: {len(main_blocks)} main + {len(adjusted_tail_blocks)} tail = {len(final_blocks)} total")
                
                return OCRDocument(
                    side=side,
                    raw_text=render_blocks_to_text(final_blocks),
                    blocks=final_blocks,
                    engine_name=self.engine_name,
                )
            
            # Side1: single pass
            psm = "6"
            print(f"[OCR] psm={psm}, lang={lang}")
            
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
                config=f"--oem 3 --psm {psm} -c preserve_interword_spaces=1",
            )
            blocks = parse_tesseract_data(data)
            print(f"[OCR] parsed {len(blocks)} blocks")
            
            return OCRDocument(
                side=side,
                raw_text=render_blocks_to_text(blocks),
                blocks=blocks,
                engine_name=self.engine_name,
            )

    def _run_with_cli(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        print(f"[OCR] backend=cli (FALLBACK), side={side.value}")
        
        with _materialize_input(file) as input_path:
            psm = "6" if side == InspectionSide.SIDE1 else "11"
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
                "gpu": False,
                "easyocr_langs": ["en"],
                "verifier": {
                    "enabled": True,
                    "min_confidence_to_skip": 0.82,
                    "min_block_width": 20,
                    "min_block_height": 12,
                    "max_blocks_per_image": 12,
                },
            },
        )
        self._preferred_engine = preferred_engine or str(config.get("engine", "auto"))
        self._lang = str(config.get("lang", "en"))
        self._use_angle_cls = bool(config.get("use_angle_cls", True))
        self._side_langs = dict(config.get("side_langs", {}))
        
        # GPU config - auto-detect hoặc force
        gpu_config = config.get("gpu", "auto")
        self._gpu = _resolve_gpu_setting(gpu_config)
        
        # EasyOCR config
        self._easyocr_langs = list(config.get("easyocr_langs", ["en"]))
        
        # Verifier config
        verifier_config = dict(config.get("verifier", {}))
        self._verifier_enabled = bool(verifier_config.get("enabled", True))
        self._min_confidence_to_skip = float(verifier_config.get("min_confidence_to_skip", 0.82))
        self._min_block_width = int(verifier_config.get("min_block_width", 20))
        self._min_block_height = int(verifier_config.get("min_block_height", 12))
        self._max_blocks_per_image = int(verifier_config.get("max_blocks_per_image", 12))
        
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
                "Install easyocr, paddleocr or tesseract, or set strict_real_ocr=false in configs/ocr.yaml."
            )

        if last_error is not None:
            raise RuntimeError(
                f"Unable to run OCR with any provider: {last_error}"
            ) from last_error
        return MockOCREngine().run(side=side, file=file)

    def _resolve_engine_order(self) -> list[str]:
        if self._preferred_engine == "auto":
            return ["ensemble", "easyocr", "paddleocr", "tesseract", "mock"]
        return [self._preferred_engine, "mock"]

    def _build_engine(self, engine_name: str) -> BaseOCREngine:
        if engine_name == "ensemble":
            return EnsembleOCREngine(
                easyocr_langs=self._easyocr_langs,
                verifier_enabled=self._verifier_enabled,
                min_confidence_to_skip=self._min_confidence_to_skip,
                min_block_width=self._min_block_width,
                min_block_height=self._min_block_height,
                max_blocks_per_image=self._max_blocks_per_image,
                gpu=self._gpu,
            )
        
        if engine_name == "easyocr":
            return EasyOCREngine(
                langs=self._easyocr_langs,
                gpu=self._gpu,
            )
        
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
