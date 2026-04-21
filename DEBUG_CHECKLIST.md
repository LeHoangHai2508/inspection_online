# Debug Checklist - Kiểm tra OCR Backend & Fixes

## ⚠️ QUAN TRỌNG: Kiểm tra backend đang chạy

### Bước 1: Kiểm tra pytesseract có được cài không

```bash
python -c "import pytesseract; print('pytesseract OK')"
python -c "from PIL import Image; print('PIL OK')"
```

**Nếu lỗi:**
```bash
pip install pytesseract pillow
```

### Bước 2: Restart server và xem log

```bash
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Bước 3: Upload template và xem terminal

**Phải thấy:**
```
[OCR] backend=pytesseract, side=side1
[OCR] psm=6, lang=eng+fra+...+ara+chi_sim
[OCR] parsed 15 blocks

[OCR] backend=pytesseract, side=side2
[OCR] psm=11, lang=eng+jpn+chi_sim+chi_tra+...
[OCR] parsed 25 blocks
```

**Nếu thấy:**
```
[OCR] backend=cli (FALLBACK), side=side1
```

→ ❌ **ĐANG CHẠY CLI FALLBACK!**
→ Parser Arabic sẽ KHÔNG hoạt động
→ Phải cài pytesseract + PIL

---

## ✅ Checklist các sửa đổi

### 1. Parser có helper Arabic ✅

**Kiểm tra:**
```bash
grep "_is_arabic_token" src/ocr/parser.py
grep "_merge_items_preserve_script_direction" src/ocr/parser.py
```

**Phải thấy:**
- `def _is_arabic_token(text: str) -> bool:`
- `def _merge_items_preserve_script_direction(items: list[dict]) -> str:`

---

### 2. Parser dùng helper Arabic ✅

**Kiểm tra:**
```bash
grep "merged_text = _merge_items_preserve_script_direction" src/ocr/parser.py
```

**Phải thấy:**
```python
merged_text = _merge_items_preserve_script_direction(items)
```

**KHÔNG được thấy:**
```python
items = sorted(items, key=lambda item: item["left"])
merged_text = " ".join(item["text"] for item in items).strip()
```

---

### 3. Side2 không có threshold ✅

**Kiểm tra:**
```bash
grep -A 5 "if heavy:" src/ocr/engine.py | grep "threshold"
```

**Phải thấy:**
```python
# Bỏ threshold cho side2 để giữ nét chữ Trung nhỏ ở cuối nhãn.
# _, image = cv2.threshold(
```

**KHÔNG được thấy:**
```python
_, image = cv2.threshold(
    image,
    0,
    255,
    cv2.THRESH_BINARY + cv2.THRESH_OTSU,
)
```

---

### 4. PSM 11 cho side2 ✅

**Kiểm tra:**
```bash
grep 'psm = "6" if side' src/ocr/engine.py
```

**Phải thấy:**
```python
psm = "6" if side == InspectionSide.SIDE1 else "11"
```

**KHÔNG được thấy:**
```python
psm = "6" if side == InspectionSide.SIDE1 else "4"
```

---

### 5. Config có đủ ngôn ngữ ✅

**Kiểm tra:**
```bash
grep "side1:" configs/ocr.yaml
grep "side2:" configs/ocr.yaml
```

**Phải thấy:**
```yaml
side1: eng+fra+deu+ita+spa+por+rus+ara+chi_sim
side2: eng+jpn+chi_sim+chi_tra+kor+tha+vie+rus
```

---

### 6. Logging đã được thêm ✅

**Kiểm tra:**
```bash
grep 'print.*\[OCR\]' src/ocr/engine.py
```

**Phải thấy:**
```python
print(f"[OCR] backend=pytesseract, side={side.value}")
print(f"[OCR] psm={psm}, lang={lang}")
print(f"[OCR] parsed {len(blocks)} blocks")
print(f"[OCR] backend=cli (FALLBACK), side={side.value}")
```

---

## 🧪 Test Flow

### 1. Restart server
```bash
# Ctrl+C để stop
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Upload template MỚI

Vào: http://localhost:8000/templates/create

### 3. Xem terminal log

**Kỳ vọng:**
```
[OCR] backend=pytesseract, side=side1
[OCR] psm=6, lang=eng+fra+deu+ita+spa+por+rus+ara+chi_sim
[OCR] parsed 12 blocks

[OCR] backend=pytesseract, side=side2
[OCR] psm=11, lang=eng+jpn+chi_sim+chi_tra+kor+tha+vie+rus
[OCR] parsed 28 blocks
```

### 4. Kiểm tra preview

**Side1:**
- ✅ "Made in Vietnam" (Latin)
- ✅ "فيتنام في" (Arabic đúng thứ tự)
- ✅ "中国 170/76A" (CJK)

**Side2:**
- ✅ Chữ Trung ở cuối đọc được
- ✅ Thứ tự dòng đúng

---

## ❌ Troubleshooting

### Vấn đề 1: Thấy "backend=cli (FALLBACK)"

**Nguyên nhân:**
- pytesseract hoặc PIL chưa cài
- Import bị lỗi

**Giải pháp:**
```bash
pip install pytesseract pillow
# Restart server
```

**Kiểm tra lại:**
```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
python -c "from PIL import Image; print('PIL OK')"
```

---

### Vấn đề 2: Arabic vẫn sai thứ tự

**Debug:**

Thêm vào `_merge_items_preserve_script_direction()`:
```python
print(f"[Parser] Processing {len(items)} items")
for i, span in enumerate(spans):
    is_arabic = _is_arabic_token(span[0]["text"])
    texts = [item["text"] for item in span]
    print(f"  Span {i} ({'Arabic' if is_arabic else 'Other'}): {texts}")
```

**Kiểm tra:**
- Span có được tách đúng không?
- Arabic span có được đảo không?

---

### Vấn đề 3: Chữ Trung cuối side2 vẫn sai

**Nếu đã:**
- ✅ Bỏ threshold
- ✅ PSM 11
- ✅ Config có chi_sim+chi_tra

**Thử tiếp:**

**Option 1: Tăng scale side2**
```python
# Trong _preprocess_for_tesseract()
fx=2.5,  # thay vì 2.0
fy=2.5,
```

**Option 2: Thử adaptive threshold**
```python
# Thay vì bỏ threshold hoàn toàn
image = cv2.adaptiveThreshold(
    image,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    11,
    2,
)
```

**Option 3: 2-pass OCR (xem docs/ARABIC_CJK_FIXES.md)**

---

### Vấn đề 4: Không thấy log [OCR]

**Nguyên nhân:**
- Server chưa restart
- Code chưa được reload

**Giải pháp:**
```bash
# Stop server (Ctrl+C)
# Start lại
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| Side1 OCR time | 500-1000ms |
| Side2 OCR time | 800-1500ms |
| Parser time | 5-10ms |
| Total per template | 1.5-3s |

---

## 📖 Docs

- `docs/ARABIC_CJK_FIXES.md` - Chi tiết Arabic & CJK fixes
- `docs/OCR_ROOT_FIXES.md` - 3 lỗi gốc
- `docs/OCR_FIXES.md` - 5 lỗi OCR ban đầu
- `FINAL_FIX_SUMMARY.md` - Tóm tắt tất cả

---

## 🎯 Quick Commands

```bash
# Kiểm tra dependencies
python -c "import pytesseract; from PIL import Image; print('OK')"

# Kiểm tra Tesseract languages
tesseract --list-langs | grep -E "(ara|chi_sim|chi_tra)"

# Kiểm tra code
grep "_merge_items_preserve_script_direction" src/ocr/parser.py
grep 'psm = "6" if side' src/ocr/engine.py
grep "# _, image = cv2.threshold" src/ocr/engine.py

# Restart server
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

---

## ✅ Final Checklist

Trước khi test, đảm bảo:

- [ ] pytesseract + PIL đã cài
- [ ] Server đã restart
- [ ] Terminal log hiển thị `backend=pytesseract`
- [ ] Parser có `_merge_items_preserve_script_direction()`
- [ ] Side2 không có threshold
- [ ] PSM = 11 cho side2
- [ ] Config có đủ ngôn ngữ
- [ ] Upload template MỚI (không dùng cũ)

**Nếu tất cả ✅ → Test ngay!**
