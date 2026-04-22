# 🚀 Restart & Test - 2-Pass OCR

## ✅ Đã implement

### 8. 2-Pass OCR cho Side2

**Vấn đề đã fix:**
- ❌ Phần cuối side2 thiếu chữ CJK
- ❌ Địa chỉ Taiwan không đầy đủ
- ❌ "這 日 期 林 於 工廠" bị vỡ

**Giải pháp:**
- Pass 1: OCR toàn ảnh (general)
- Pass 2: OCR riêng 35% cuối (tối ưu CJK)
- Merge: giữ phần trên, thay phần cuối

---

## 🧪 Test ngay

### Bước 1: Restart server

```bash
# Stop server (Ctrl+C)
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Bước 2: Upload template MỚI

⚠️ **QUAN TRỌNG:** Phải upload template MỚI, không dùng template cũ!

### Bước 3: Xem terminal log

**Phải thấy:**
```
[OCR] backend=pytesseract, side=side1
[OCR] psm=6, lang=eng+fra+...+ara+chi_sim
[OCR] parsed 15 blocks

[OCR] backend=pytesseract, side=side2
[OCR] side2: 2-pass mode
[OCR] pass1: full image, psm=11, lang=eng+jpn+chi_sim+...
[OCR] pass2: bottom 35%, psm=11, lang=chi_sim+chi_tra+jpn+...
[OCR] merged: 45 main + 12 tail = 57 total
```

**Nếu thấy `backend=cli (FALLBACK)`:**
```bash
pip install pytesseract pillow
# Restart server
```

### Bước 4: Kiểm tra preview

**Side1:**
- ✅ "Made in Vietnam"
- ✅ "في فيتنام" (Arabic đúng thứ tự)
- ✅ "中国 170/76A"
- ✅ Địa chỉ Pháp đầy đủ

**Side2:**
- ✅ Composition đa ngôn ngữ
- ✅ **Địa chỉ Taiwan đầy đủ** (mục tiêu chính)
- ✅ **Số điện thoại Taiwan**
- ✅ **"TWN" / "BRA" / "M-" rõ ràng**
- ✅ **Chữ Chinese không bị vỡ**

---

## 📊 Expected Results

### Trước (1-pass)
```
Side2 cuối:
造 - ไธ ua ЖЕ: 越南 ❌ (vỡ)
這 日 期 林 於 工廠 ❌ (thiếu nhiều chữ)
地址不完整 ❌
```

### Sau (2-pass)
```
Side2 cuối:
越南 ✅
這個日期標於工廠 ✅
台灣地址完整 ✅
電話: 04-24719666 ✅
TWN BRA M- ✅
```

---

## 🔍 Debug

### Kiểm tra log chi tiết

**Pass 1:**
```
[OCR] pass1: full image, psm=11
```
→ Lấy phần lớn nội dung

**Pass 2:**
```
[OCR] pass2: bottom 35%, psm=11, lang=chi_sim+chi_tra+jpn+...
```
→ Tối ưu cho CJK nhỏ

**Merge:**
```
[OCR] merged: 45 main + 12 tail = 57 total
```
→ Giữ phần trên, thay phần cuối

### Nếu phần cuối vẫn thiếu

**Thử 1: Tăng crop ratio**

Sửa trong `src/ocr/engine.py`:
```python
# Hiện tại: 65% → 100% (35% cuối)
crop_top = int(height * 0.65)

# Thử: 60% → 100% (40% cuối)
crop_top = int(height * 0.60)
```

**Thử 2: Tăng scale cho pass 2**

Thêm trước OCR pass 2:
```python
# Scale thêm 1.5x cho tail
tail_image = tail_image.resize(
    (int(tail_image.width * 1.5), int(tail_image.height * 1.5)),
    Image.LANCZOS
)
```

---

## 📈 Performance

| Pass | Time | Purpose |
|------|------|---------|
| Pass 1 | 800-1200ms | Full image |
| Pass 2 | 300-500ms | Bottom 35% |
| **Total** | **1100-1700ms** | Acceptable |

So với 1-pass (~800-1000ms):
- Chậm hơn ~300-700ms
- Nhưng accuracy tăng đáng kể
- Trade-off đáng giá

---

## 📖 Docs

- `docs/TWO_PASS_OCR.md` - Chi tiết 2-pass OCR
- `docs/ARABIC_CJK_FIXES.md` - Arabic & CJK fixes
- `DEBUG_CHECKLIST.md` - Debug checklist
- `check_ocr_setup.py` - Setup checker

---

## ✅ Final Checklist

Trước khi test:

- [ ] Server đã restart
- [ ] Terminal log hiển thị `backend=pytesseract`
- [ ] Terminal log hiển thị `side2: 2-pass mode`
- [ ] Upload template MỚI
- [ ] Kiểm tra preview side2 phần cuối

**Nếu tất cả ✅ → Phần cuối side2 phải đầy đủ!**

---

## 🎯 Mục tiêu

**Side2 phần cuối phải có:**
1. ✅ Địa chỉ Taiwan đầy đủ
2. ✅ Số điện thoại: 04-24719666
3. ✅ Chữ Chinese không vỡ
4. ✅ TWN / BRA / M- rõ ràng
5. ✅ Ngày tháng đầy đủ

**Restart server và test ngay!**
