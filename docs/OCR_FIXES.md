# OCR Fixes - Chi tiết 5 lỗi đã sửa

## Tổng quan

Code trước đây có 5 lỗi nghiêm trọng khiến OCR đọc sai, đặc biệt là side2 (mặt sau với nhiều ngôn ngữ).

## 5 lỗi đã sửa

### ❌ Lỗi 1: Side2 không scale thực tế

**Vấn đề:**
```python
# Comment nói "Scale 2x" nhưng code lại:
image = cv2.resize(
    image,
    None,
    fx=1.0,  # ❌ Không scale!
    fy=1.0,  # ❌ Không scale!
    interpolation=cv2.INTER_CUBIC,
)
```

**Hậu quả:**
- Chữ nhỏ ở side2 không được phóng to
- Tesseract khó đọc chữ nhỏ, đặc biệt là Trung/Nhật/Hàn/Thái/Ả Rập

**✅ Đã sửa:**
```python
image = cv2.resize(
    image,
    None,
    fx=2.0,  # ✅ Scale 2x
    fy=2.0,  # ✅ Scale 2x
    interpolation=cv2.INTER_CUBIC,
)
```

---

### ❌ Lỗi 2: Denoise làm mất nét chữ nhỏ

**Vấn đề:**
```python
# Side2 đang bị denoise quá mạnh
image = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
```

**Hậu quả:**
- Mất dấu chấm, dấu phẩy
- Mất nét rất mảnh của chữ Trung/Nhật/Hàn/Thái/Ả Rập
- Chữ nhỏ bị blur, Tesseract đọc sai

**✅ Đã sửa:**
```python
# Tắt denoise hoàn toàn
# image = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
```

**Lý do:**
- Denoise phù hợp với ảnh nhiễu cao (scan cũ, chụp tối)
- Template của bạn là ảnh chất lượng tốt → không cần denoise
- Giữ nét chữ quan trọng hơn giảm noise

---

### ❌ Lỗi 3: PSM mode không phù hợp

**Vấn đề:**
```python
# Cả 2 sides đều dùng PSM 3
psm = "3"  # Fully automatic layout
```

**Hậu quả:**
- PSM 3 không tối ưu cho:
  - Side1: text block đơn giản
  - Side2: nhiều block, nhiều ngôn ngữ
- Tesseract tự động phát hiện layout → dễ sai
- Đảo thứ tự từ (ví dụ: "Made Vietnam" thay vì "Made in Vietnam")

**✅ Đã sửa:**
```python
# Tách PSM theo side
psm = "6" if side == InspectionSide.SIDE1 else "4"
```

**PSM modes:**
- PSM 6: Uniform block of text (phù hợp side1)
- PSM 4: Single column of text (phù hợp side2 với nhiều dòng)

**Thêm preserve_interword_spaces:**
```python
config=f"--oem 3 --psm {psm} -c preserve_interword_spaces=1"
```

---

### ❌ Lỗi 4: OCR quá nhiều ngôn ngữ cùng lúc

**Vấn đề:**
```python
# Trước đây có thể dùng:
lang = "eng+fra+deu+ita+spa+por+rus+ara+jpn+chi_sim+chi_tra+kor+tha+vie"
# cho cả 2 sides
```

**Hậu quả:**
- Tesseract chậm (phải check tất cả language models)
- Dễ nhiễu (lẫn glyph giữa các ngôn ngữ)
- Side1 không cần Trung/Nhật/Hàn/Thái/Việt

**✅ Đã sửa:**

Code đã hỗ trợ `side_langs` từ trước:
```python
def _lang_for_side(self, side: InspectionSide) -> str:
    """Lấy ngôn ngữ phù hợp cho side, fallback về lang chung"""
    return self._side_langs.get(side.value, self._lang)
```

Config `configs/ocr.yaml`:
```yaml
engine: tesseract
side_langs:
  side1: eng+fra+deu+ita+spa+por+rus+ara
  side2: eng+jpn+chi_sim+chi_tra+kor+tha+vie+rus
lang: eng  # fallback
```

**Lợi ích:**
- Side1: chỉ OCR ngôn ngữ châu Âu + Ả Rập
- Side2: thêm Trung/Nhật/Hàn/Thái/Việt
- Nhanh hơn, chính xác hơn

---

### ❌ Lỗi 5: CLAHE clipLimit quá cao

**Vấn đề:**
```python
# Side2 dùng clipLimit quá cao
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
```

**Hậu quả:**
- Tăng contrast quá mạnh
- Làm nổi noise
- Chữ nhỏ bị "cháy" (over-contrast)

**✅ Đã sửa:**
```python
# Side2: giảm clipLimit
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

# Side1: giữ nhẹ
clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(8, 8))
```

---

## Code sau khi sửa

### `_preprocess_for_tesseract()`

```python
def _preprocess_for_tesseract(input_path: Path, heavy: bool = True):
    """
    Preprocess ảnh cho Tesseract.
    - side1: nhẹ, giữ nét
    - side2: scale 2x + CLAHE + threshold, không denoise
    """
    from PIL import Image

    image = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"Cannot read image for OCR: {input_path}")

    if heavy:
        # Side2: chữ nhỏ, nhiều ngôn ngữ
        # ✅ Scale 2x để chữ nhỏ rõ hơn
        image = cv2.resize(
            image,
            None,
            fx=2.0,
            fy=2.0,
            interpolation=cv2.INTER_CUBIC,
        )

        # ✅ CLAHE vừa phải
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        image = clahe.apply(image)

        # ✅ Threshold để tách nét chữ
        _, image = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        # ✅ Tắt denoise
        # image = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
    else:
        # Side1: chữ lớn hơn, chỉ cần contrast nhẹ
        clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(8, 8))
        image = clahe.apply(image)

    return Image.fromarray(image)
```

### `_run_with_pytesseract()`

```python
def _run_with_pytesseract(self, side, file):
    import pytesseract
    from PIL import Image

    with _materialize_input(file) as input_path:
        heavy = side == InspectionSide.SIDE2
        image = _preprocess_for_tesseract(input_path, heavy=heavy)
        
        # ✅ PSM theo side
        psm = "6" if side == InspectionSide.SIDE1 else "4"
        
        # ✅ Lang theo side
        lang = self._lang_for_side(side)
        
        # ✅ Preserve spaces
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
```

### `_run_with_cli()`

```python
def _run_with_cli(self, side, file):
    with _materialize_input(file) as input_path:
        # ✅ PSM theo side
        psm = "6" if side == InspectionSide.SIDE1 else "4"
        
        # ✅ Lang theo side
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
```

---

## Cách test

### 1. Restart server

```bash
# Stop server hiện tại
# Ctrl+C

# Start lại
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Upload template mới

1. Vào UI template creation
2. Upload ảnh side1 và side2
3. Xem OCR output

### 3. Kiểm tra kết quả

**Side1 nên:**
- Đọc đúng thứ tự từ
- Không bị đảo "Made Vietnam" → "Made in Vietnam"
- Giữ được spaces

**Side2 nên:**
- Đọc được chữ nhỏ
- Đọc được đa ngôn ngữ (Trung/Nhật/Hàn/Thái/Việt)
- Không bị vỡ dòng quá nhiều
- Giữ được dấu chấm, dấu phẩy

---

## Nếu vẫn sai

### Option 1: Điều chỉnh preprocessing

**Nếu side2 vẫn mất chữ nhỏ:**

```python
# Thử bỏ threshold
if heavy:
    image = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    image = clahe.apply(image)
    # Bỏ threshold
    # _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
```

**Nếu side2 vẫn nhiễu:**

```python
# Thử adaptive threshold thay vì Otsu
image = cv2.adaptiveThreshold(
    image,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    11,
    2,
)
```

### Option 2: Thử PSM khác

```python
# PSM 3: Fully automatic (default)
# PSM 4: Single column
# PSM 6: Uniform block
# PSM 11: Sparse text
# PSM 12: Sparse text with OSD

# Thử cho side2:
psm = "11"  # hoặc "12"
```

### Option 3: Chuyển sang PaddleOCR

Code đã hỗ trợ PaddleOCR. Trong `configs/ocr.yaml`:

```yaml
engine: paddleocr  # thay vì tesseract
lang: en
use_angle_cls: true
```

PaddleOCR thường tốt hơn với:
- Chữ nghiêng
- Nhiều ngôn ngữ châu Á
- Layout phức tạp

---

## So sánh trước/sau

### Trước (5 lỗi)

```python
# ❌ Không scale
fx=1.0, fy=1.0

# ❌ Denoise mất nét
cv2.fastNlMeansDenoising(...)

# ❌ PSM 3 cho cả 2 sides
psm = "3"

# ❌ Quá nhiều ngôn ngữ
lang = "eng+fra+...+jpn+chi_sim+..."

# ❌ CLAHE quá mạnh
clipLimit=2.5
```

**Kết quả:**
- Side1: "Made Vietnam" (sai thứ tự)
- Side2: Vỡ nhiều dòng, lẫn glyph, mất dấu

### Sau (đã sửa)

```python
# ✅ Scale 2x
fx=2.0, fy=2.0

# ✅ Không denoise
# cv2.fastNlMeansDenoising(...)

# ✅ PSM theo side
psm = "6" if side1 else "4"

# ✅ Lang theo side
side_langs: {side1: "eng+...", side2: "eng+jpn+..."}

# ✅ CLAHE vừa phải
clipLimit=2.0 (side2), 1.0 (side1)
```

**Kết quả mong đợi:**
- Side1: "Made in Vietnam" (đúng)
- Side2: Đọc đúng đa ngôn ngữ, giữ được dấu

---

## Monitoring

Sau khi deploy, theo dõi:

1. **OCR accuracy**: % templates đọc đúng
2. **Processing time**: Thời gian OCR mỗi side
3. **Error rate**: % templates bị reject do OCR sai

```python
# Thêm logging
logger.info(f"OCR side={side}, lang={lang}, psm={psm}, time={elapsed}ms")
```

---

## Tài liệu tham khảo

- [Tesseract PSM modes](https://github.com/tesseract-ocr/tesseract/blob/main/doc/tesseract.1.asc#page-segmentation-modes)
- [CLAHE parameters](https://docs.opencv.org/4.x/d5/daf/tutorial_py_histogram_equalization.html)
- [Tesseract language data](https://github.com/tesseract-ocr/tessdata)
