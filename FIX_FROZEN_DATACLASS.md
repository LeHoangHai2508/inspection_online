# Fix - Frozen Dataclass Error

## ❌ Lỗi

```
RuntimeError: cannot assign to field 'line_index'
```

## 🔍 Nguyên nhân

`OCRBlock` là `frozen=True` dataclass:
```python
@dataclass(frozen=True)
class OCRBlock:
    text: str
    bbox: BoundingBox
    confidence: float
    line_index: int
```

→ Không thể modify sau khi tạo
→ Không thể: `block.line_index = i`

## ✅ Đã fix

**Trước (SAI):**
```python
# Re-sort và re-index
merged_blocks = sorted(merged_blocks, key=lambda b: (b.bbox.y1, b.bbox.x1))
for i, block in enumerate(merged_blocks, start=1):
    block.line_index = i  # ❌ Lỗi: cannot assign
```

**Sau (ĐÚNG):**
```python
# Re-sort
merged_blocks = sorted(merged_blocks, key=lambda b: (b.bbox.y1, b.bbox.x1))

# Tạo lại blocks với line_index mới
final_blocks = []
for i, block in enumerate(merged_blocks, start=1):
    final_blocks.append(
        OCRBlock(
            text=block.text,
            bbox=block.bbox,
            confidence=block.confidence,
            line_index=i,  # ✅ Tạo block mới với line_index đúng
        )
    )
```

## 🚀 Test lại

Server đã tự reload. Chỉ cần:

**Upload template lại**

**Kỳ vọng:**
```
[OCR] backend=pytesseract, side=side2
[OCR] side2: 2-pass mode
[OCR] pass1: full image, psm=11
[OCR] pass2: bottom 35%, psm=11
[OCR] merged: 45 main + 12 tail = 57 total
```

**Không còn lỗi!** ✅

Side2 phần cuối phải đầy đủ:
- ✅ Địa chỉ Taiwan
- ✅ Số điện thoại
- ✅ Chữ Chinese không vỡ
- ✅ TWN / BRA / M-
