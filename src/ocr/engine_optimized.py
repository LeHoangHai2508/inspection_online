"""
OCR Engine - Optimized version with caching and language profiles

Key improvements:
1. Removed CUDA_VISIBLE_DEVICES=-1 to allow GPU usage
2. Added engine caching to avoid recreating readers
3. Added language profiles instead of loading all languages
4. Reduced preprocessing scale factors
5. Separated fast mode (easyocr) from accurate mode (ensemble)
"""
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

# REMOVED: os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
# This was blocking GPU usage. Now GPU is controlled by config only.

# Keep PaddleOCR CPU-only settings
os.environ['FLAGS_use_mkldnn'] = '0'

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


def _detect_gpu_available() -> bool:
    """
    Tự động detect GPU có available không.
    Chỉ kiểm tra PyTorch (EasyOCR) vì đó là engine chính.
    """
    try:
        import torch
        has_cuda = torch.cuda.is_available()
        if has_cuda:
            print(f"[GPU] PyTorch CUDA available → Using GPU")
        else:
            print(f"[GPU] PyTorch CUDA not available → Using CPU")
        return has_cuda
    except Exception:
        print(f"[GPU] PyTorch not installed → Using CPU")
        return False


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


def _preprocess_for_easyocr(input_path: Path, side: InspectionSide) -> np.ndarray:
    """
    Preprocess nhẹ cho EasyOCR.
    OPTIMIZED: Giảm scale factor để nhanh hơn.
    """
    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Cannot read image for OCR: {input_path}")

    # Crop footer noise cho side2
    if side == InspectionSide.SIDE2:
        h, w = image.shape[:2]
        crop_bottom = int(h * 0.90)
        image = image[:crop_bottom, :]

    # OPTIMIZED: Giảm scale từ 1.6/2.0 xuống 1.2/1.4
    scale = 1.2 if side == InspectionSide.SIDE1 else 1.4
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
        self._reader = easyocr.Reader(langs, gpu=gpu, verbose=False)
        self._gpu = gpu
        self._langs = langs

    def run(self, side: InspectionSide, file: TemplateUploadFile) -> OCRDocument:
        print(f"[EasyOCR] Running OCR on {side.value} (GPU={self._gpu}, profile={self._langs})")
        
        with _materialize_input(file) as input_path:
            image = _preprocess_for_easyocr(input_path, side)
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
    Verifier cho hard blocks (chỉ dùng trong ensemble mode).
    """
    def __init__(self) -> None:
        if importlib.util.find_spec("keras_ocr") is None:
            raise RuntimeError("keras_ocr is not installed.")

        import keras_ocr  # type: ignore
        print("[KerasOCR] Initializing verifier...")
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

    if new_confidence < old_block.confidence and new_len < old_len:
        return False

    if old_block.confidence < 0.75 and new_len >= old_len:
        return True

    if old_len <= 2 and new_len > old_len:
        return True

    return False


class EnsembleOCREngine(BaseOCREngine):
    """
    Ensemble mode: EasyOCR + KerasOCR verifier.
    Chỉ dùng khi cần độ chính xác cao nhất.
    """
    engine_name = "ensemble"

    def __init__(
        self,
        easyocr_langs: list[str],
        verifier_enabled: bool = True,
        min_confidence_to_skip: float = 0.60,
        min_block_width: int = 20,
        min_block_height: int = 12,
        max_blocks_per_image: int = 3,
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
            image = _preprocess_for_easyocr(input_path, side)

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
                print(f"[Ensemble] Block {idx}/{len(hard_blocks)}: '{block.text[:20]}...' → '{new_text[:20]}...'")
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


class AutoOCREngine(BaseOCREngine):
    """
    Auto OCR Engine with caching and language profiles.
    
    Key improvements:
    1. Cache readers to avoid recreating them
    2. Support language profiles instead of loading all languages
    3. GPU control via config only (no hardcoded CUDA_VISIBLE_DEVICES)
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
                "gpu": "auto",
                "strict_real_ocr": False,
                "easyocr_profiles": {
                    "latin_basic": ["en", "vi"],
                },
                "default_profile": "latin_basic",
                "verifier": {
                    "enabled": False,
                    "min_confidence_to_skip": 0.60,
                    "min_block_width": 20,
                    "min_block_height": 12,
                    "max_blocks_per_image": 3,
                },
            },
        )
        
        self._preferred_engine = preferred_engine or str(config.get("engine", "auto"))
        
        # GPU config
        gpu_config = config.get("gpu", "auto")
        self._gpu = _resolve_gpu_setting(gpu_config)
        
        # Language profiles
        self._easyocr_profiles = dict(config.get("easyocr_profiles", {}))
        self._default_profile = str(config.get("default_profile", "latin_basic"))
        
        # Verifier config
        verifier_config = dict(config.get("verifier", {}))
        self._verifier_enabled = bool(verifier_config.get("enabled", False))
        self._min_confidence_to_skip = float(verifier_config.get("min_confidence_to_skip", 0.60))
        self._min_block_width = int(verifier_config.get("min_block_width", 20))
        self._min_block_height = int(verifier_config.get("min_block_height", 12))
        self._max_blocks_per_image = int(verifier_config.get("max_blocks_per_image", 3))
        
        # Strict mode
        if strict_real_ocr is not None:
            self._strict = strict_real_ocr
        else:
            self._strict = bool(config.get("strict_real_ocr", False))
        
        # CACHE: Giữ engines đã tạo để không phải tạo lại
        self._engine_cache: dict[str, BaseOCREngine] = {}
        
        print(f"[AutoOCR] Initialized: engine={self._preferred_engine}, gpu={self._gpu}, profile={self._default_profile}")

    def run(
        self,
        side: InspectionSide,
        file: TemplateUploadFile,
        profile_name: str | None = None,
    ) -> OCRDocument:
        """
        Run OCR with optional language profile.
        
        Args:
            side: Side1 or Side2
            file: Image file
            profile_name: Language profile name (e.g., "latin_basic", "cjk")
                         If None, uses default_profile from config
        """
        profile = profile_name or self._default_profile
        engine_key = f"{self._preferred_engine}:{profile}"
        
        # CACHE: Kiểm tra cache trước
        engine = self._engine_cache.get(engine_key)
        if engine is None:
            print(f"[AutoOCR] Building new engine: {engine_key}")
            engine = self._build_engine(self._preferred_engine, profile)
            self._engine_cache[engine_key] = engine
        else:
            print(f"[AutoOCR] Using cached engine: {engine_key}")
        
        try:
            return engine.run(side=side, file=file)
        except Exception as exc:
            if self._strict:
                raise RuntimeError(
                    f"strict_real_ocr=True but OCR failed: {exc}. "
                    "Install easyocr, paddleocr or tesseract, or set strict_real_ocr=false in configs/ocr.yaml."
                ) from exc
            
            # Fallback to mock
            print(f"[AutoOCR] Engine failed, falling back to mock: {exc}")
            return MockOCREngine().run(side=side, file=file)

    def _build_engine(self, engine_name: str, profile_name: str) -> BaseOCREngine:
        """
        Build engine với language profile cụ thể.
        """
        # Lấy danh sách ngôn ngữ từ profile
        langs = self._easyocr_profiles.get(profile_name, ["en"])
        
        if engine_name == "easyocr":
            return EasyOCREngine(
                langs=langs,
                gpu=self._gpu,
            )
        
        if engine_name == "ensemble":
            return EnsembleOCREngine(
                easyocr_langs=langs,
                verifier_enabled=self._verifier_enabled,
                min_confidence_to_skip=self._min_confidence_to_skip,
                min_block_width=self._min_block_width,
                min_block_height=self._min_block_height,
                max_blocks_per_image=self._max_blocks_per_image,
                gpu=self._gpu,
            )
        
        if engine_name == "paddleocr":
            from paddleocr import PaddleOCR  # type: ignore
            return PaddleOCREngine(lang="en", use_angle_cls=True)
        
        if engine_name == "tesseract":
            # Tesseract không cần profile vì dùng lang string
            return TesseractOCREngine(lang="eng")
        
        return MockOCREngine()


class TesseractOCREngine(BaseOCREngine):
    """Tesseract OCR engine (fallback)."""
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
            image = Image.open(input_path)
            
            data = pytesseract.image_to_data(
                image,
                lang=self._lang,
                output_type=pytesseract.Output.DICT,
                config=f"--oem 3 --psm 6 -c preserve_interword_spaces=1",
            )
            
            from src.ocr.parser import parse_tesseract_data
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


class _materialize_input:
    def __init__(self, file: TemplateUploadFile) -> None:
        self._file = file
        self._path: Path | None = None

    def __enter__(self) -> Path:
        suffix = Path(self._file.filename).suffix or ".bin"
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.write(fd, self._file.content)
        os.close(fd)
        self._path = Path(path)
        return self._path

    def __exit__(self, *args: Any) -> None:
        if self._path and self._path.exists():
            self._path.unlink()
