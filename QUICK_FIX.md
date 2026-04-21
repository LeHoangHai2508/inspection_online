# Quick Fix - BoundingBox Import Error

## ❌ Lỗi

```
RuntimeError: name 'BoundingBox' is not defined
```

## ✅ Đã fix

**File:** `src/ocr/engine.py`

**Thêm import:**
```python
from src.domain.models import BoundingBox, OCRBlock, TemplateUploadFile
```

**Trước:**
```python
from src.domain.models import OCRBlock, TemplateUploadFile
```

## 🚀 Test lại

```bash
# Server đã tự reload (--reload mode)
# Hoặc restart thủ công:
# Ctrl+C
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

## ✅ Upload template lại

Bây giờ sẽ thấy:
```
[OCR] backend=pytesseract, side=side1
[OCR] psm=6, lang=eng+fra+...
[OCR] parsed 33 blocks

[OCR] backend=pytesseract, side=side2
[OCR] side2: 2-pass mode
[OCR] pass1: full image, psm=11
[OCR] pass2: bottom 35%, psm=11
[OCR] merged: X main + Y tail = Z total
```

**Không còn lỗi!** ✅
