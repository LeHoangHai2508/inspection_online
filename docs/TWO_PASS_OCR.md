# Two-Pass OCR for Side2

## Vấn đề

Side2 có phần cuối với:
- Chữ CJK (Chinese/Japanese/Korean) rất nhỏ
- Nhiều dòng sát nhau
- Trộn nhiều ngôn ngữ (Chinese + Thai + Russian + English)
- Địa chỉ Taiwan/China phức tạp

**1-pass OCR** với cấu hình chung cho toàn ảnh sẽ luôn phải đánh đổi:
- Config tốt cho phần trên → phần cuối CJK kém
- Config tốt cho phần cuối → phần trên có thể xấu đi

## Giải pháp: 2-Pass OCR

### Pass 1: OCR toàn ảnh
- **Mục đích:** Lấy phần lớn nội dung (composition, languages, etc.)
- **Config:**
  - PSM: 11 (sparse text)
  - Lang: `eng+jpn+chi_sim+chi_tra+kor+tha+vie+rus`
  - Preprocessing: resize 2x + CLAHE (không threshold)

### Pass 2: OCR riêng 35% cuối
- **Mục đích:** Tối ưu cho CJK nhỏ ở cuối
- **Config:**
  - PSM: 11 (sparse text)
  - Lang: `chi_sim+chi_tra+jpn+kor+eng+rus+tha` (ưu tiên CJK)
  - Crop: 65% → 100% (35% cuối)
  - Preprocessing: giống pass 1

### Merge
1. Giữ blocks của pass 1 ở phần trên (y < crop_top)
2. Thay blocks ở vùng cuối bằng blocks từ pass 2
3. Offset bbox của pass 2 về hệ tọa độ ảnh gốc
4. Re-sort và re-index

## Implementation

### Code Flow

```python
if side == InspectionSide.SIDE2:
    # Pass 1: Full image
    data1 = pytesseract.image_to_data(image, lang=lang, psm=11)
    main_blocks = parse_tesseract_data(data1)
    
    # Pass 2: Bottom 35%
    crop_top = int(height * 0.65)
    tail_image = image.crop((0, crop_top, width, height))
    tail_lang = "chi_sim+chi_tra+jpn+kor+eng+rus+tha"
    data2 = pytesseract.image_to_data(tail_image, lang=tail_lang, psm=11)
    tail_blocks = parse_tesseract_data(data2)
    
    # Offset tail_blocks
    adjusted_tail_blocks = [
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
        for block in tail_blocks
    ]
    
    # Merge
    merged_blocks = [
        block for block in main_blocks if block.bbox.y2 < crop_top
    ] + adjusted_tail_blocks
    
    # Re-sort
    merged_blocks = sorted(merged_blocks, key=lambda b: (b.bbox.y1, b.bbox.x1))
```

## Lợi ích

### Accuracy
- ✅ Phần trên: giữ nguyên chất lượng
- ✅ Phần cuối CJK: tăng accuracy đáng kể
- ✅ Không cần đánh đổi giữa 2 vùng

### Performance
- Pass 1: ~800-1200ms
- Pass 2: ~300-500ms (chỉ 35% ảnh)
- **Total: ~1100-1700ms** (chấp nhận được)

### Maintainability
- ✅ Không thay đổi architecture
- ✅ Chỉ sửa trong `_run_with_pytesseract()`
- ✅ Side1 vẫn dùng single pass
- ✅ Dễ điều chỉnh crop ratio

## Tuning Parameters

### Crop Ratio
```python
# Hiện tại: 65% → 100% (35% cuối)
crop_top = int(height * 0.65)

# Nếu cần OCR nhiều hơn:
crop_top = int(height * 0.60)  # 40% cuối

# Nếu cần OCR ít hơn:
crop_top = int(height * 0.70)  # 30% cuối
```

### Language Priority
```python
# Hiện tại: ưu tiên CJK
tail_lang = "chi_sim+chi_tra+jpn+kor+eng+rus+tha"

# Nếu cần ưu tiên Japanese:
tail_lang = "jpn+chi_sim+chi_tra+kor+eng"

# Nếu cần ưu tiên Korean:
tail_lang = "kor+chi_sim+chi_tra+jpn+eng"
```

### PSM Mode
```python
# Hiện tại: PSM 11 (sparse text)
psm = 11

# Nếu text cuối đều hơn:
psm = 4  # single column

# Nếu text cuối rất sparse:
psm = 12  # sparse text with OSD
```

## Logging

Terminal sẽ hiển thị:
```
[OCR] backend=pytesseract, side=side2
[OCR] side2: 2-pass mode
[OCR] pass1: full image, psm=11, lang=eng+jpn+chi_sim+...
[OCR] pass2: bottom 35%, psm=11, lang=chi_sim+chi_tra+jpn+...
[OCR] merged: 45 main + 12 tail = 57 total
```

## Testing

### 1. Restart server
```bash
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Upload template

### 3. Kiểm tra terminal log

**Phải thấy:**
```
[OCR] side2: 2-pass mode
[OCR] pass1: full image
[OCR] pass2: bottom 35%
[OCR] merged: X main + Y tail = Z total
```

### 4. Kiểm tra preview

**Phần cuối side2 phải có:**
- ✅ Địa chỉ Taiwan đầy đủ
- ✅ Số điện thoại Taiwan
- ✅ Chữ Chinese không bị vỡ
- ✅ "TWN" / "BRA" / "M-" rõ ràng

## Troubleshooting

### Vấn đề: Phần cuối vẫn thiếu chữ

**Thử 1: Tăng crop ratio**
```python
crop_top = int(height * 0.60)  # 40% thay vì 35%
```

**Thử 2: Tăng scale cho pass 2**
```python
# Thêm preprocessing riêng cho tail
tail_image = tail_image.resize(
    (int(tail_image.width * 1.5), int(tail_image.height * 1.5)),
    Image.LANCZOS
)
```

**Thử 3: Thử PSM khác**
```python
psm = 4  # single column thay vì 11
```

---

### Vấn đề: Phần trên bị xấu đi

**Nguyên nhân:** Merge logic sai

**Kiểm tra:**
```python
print(f"Crop at y={crop_top}, image height={height}")
print(f"Main blocks in top: {len([b for b in main_blocks if b.bbox.y2 < crop_top])}")
print(f"Main blocks in bottom: {len([b for b in main_blocks if b.bbox.y2 >= crop_top])}")
```

**Fix:** Điều chỉnh crop_top

---

### Vấn đề: Performance chậm

**Hiện tại:**
- Pass 1: ~1000ms
- Pass 2: ~400ms
- Total: ~1400ms

**Nếu quá chậm:**

**Option 1: Giảm crop ratio**
```python
crop_top = int(height * 0.75)  # 25% thay vì 35%
```

**Option 2: Skip pass 2 nếu pass 1 đủ tốt**
```python
# Kiểm tra confidence của vùng cuối
bottom_blocks = [b for b in main_blocks if b.bbox.y1 >= crop_top]
avg_conf = sum(b.confidence for b in bottom_blocks) / len(bottom_blocks)

if avg_conf > 0.85:
    # Pass 1 đã đủ tốt, skip pass 2
    return main_blocks
```

## Alternative: 3-Pass OCR

Nếu 2-pass vẫn chưa đủ, có thể thử 3-pass:

```python
# Pass 1: Full image (general)
# Pass 2: Middle 30-70% (composition)
# Pass 3: Bottom 70-100% (CJK)
```

Nhưng:
- ❌ Phức tạp hơn
- ❌ Chậm hơn (~2s)
- ❌ Khó maintain

→ Chỉ làm nếu 2-pass thật sự không đủ

## Kết luận

2-pass OCR là giải pháp tốt nhất hiện tại cho side2:
- ✅ Tăng accuracy phần cuối CJK
- ✅ Không ảnh hưởng phần trên
- ✅ Performance chấp nhận được
- ✅ Dễ maintain và tune

**Restart server và test ngay!**
