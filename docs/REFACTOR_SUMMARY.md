# Refactor Summary: Ensemble OCR Engine

## Thực hiện

Đã refactor OCR engine từ Tesseract sang **Ensemble OCR** (EasyOCR + KerasOCR verifier) theo đúng kiến trúc hiện tại.

## Files đã thay đổi

### 1. `requirements.txt`
- ✓ Thêm `easyocr`
- ✓ Thêm `keras-ocr`
- ✓ Thêm `tensorflow`

### 2. `configs/ocr.yaml`
- ✓ Đổi `engine: tesseract` → `engine: ensemble`
- ✓ Thêm `easyocr_langs` (14 ngôn ngữ)
- ✓ Thêm `verifier` config
- ✓ Cập nhật `providers`

### 3. `src/ocr/engine.py`
- ✓ Import `PIL.Image` ở đầu file
- ✓ Thêm `_preprocess_for_ensemble()` helper
- ✓ Thêm `EasyOCREngine` class
- ✓ Thêm `KerasOCRVerifier` class
- ✓ Thêm `_is_hard_block()` helper
- ✓ Thêm `_crop_block()` helper
- ✓ Thêm `_should_replace_block()` helper
- ✓ Thêm `EnsembleOCREngine` class
- ✓ Cập nhật `AutoOCREngine.__init__()` để đọc config mới
- ✓ Cập nhật `AutoOCREngine._resolve_engine_order()`
- ✓ Cập nhật `AutoOCREngine._build_engine()`

### 4. Files mới tạo
- ✓ `check_ensemble_setup.py` - Script kiểm tra cài đặt
- ✓ `test_ensemble_engine.py` - Script test engine
- ✓ `ENSEMBLE_OCR_MIGRATION.md` - Hướng dẫn migration
- ✓ `REFACTOR_SUMMARY.md` - File này

## Files KHÔNG thay đổi

- ✓ `src/ocr/workflow.py` - Giữ nguyên
- ✓ `src/ocr/service.py` - Giữ nguyên
- ✓ `src/api/routes/` - Giữ nguyên
- ✓ `src/domain/models.py` - Giữ nguyên
- ✓ `run_ocr.py` - Giữ nguyên

## Kiến trúc

```
┌─────────────────────────────────────────────────────────┐
│                    OCRWorkflow                          │
│  (không đổi - chỉ gọi engine.run())                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              AutoOCREngine (updated)                    │
│  - Đọc config mới (easyocr_langs, verifier)            │
│  - Build engine theo config                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           EnsembleOCREngine (NEW)                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 1. EasyOCR đọc toàn ảnh                           │  │
│  │ 2. Tạo OCRBlock ban đầu                           │  │
│  │ 3. Chọn hard blocks                               │  │
│  │ 4. KerasOCR verify hard blocks                    │  │
│  │ 5. Merge blocks                                   │  │
│  │ 6. Trả OCRDocument                                │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  Components:                                             │
│  - EasyOCREngine (primary)                              │
│  - KerasOCRVerifier (verifier)                          │
└──────────────────────────────────────────────────────────┘
```

## Output format (không đổi)

```python
OCRDocument(
    side: InspectionSide,
    raw_text: str,           # Từ render_blocks_to_text()
    blocks: list[OCRBlock],  # Danh sách blocks
    engine_name: str,        # "ensemble"
)
```

## Hard blocks detection

Blocks được verify khi:

1. **Confidence thấp**: `confidence < 0.82`
2. **Side1 + Arabic**: Chứa ký tự U+0600 - U+06FF
3. **Side2 + vùng cuối**: `y1 >= 62%` chiều cao ảnh

Giới hạn: Tối đa 12 blocks/ảnh

## Config mặc định

```yaml
engine: ensemble

easyocr_langs:
  - en, fr, de, it, es, pt, ru
  - ar
  - ch_sim, ch_tra, ja, ko, th, vi

verifier:
  enabled: true
  min_confidence_to_skip: 0.82
  min_block_width: 20
  min_block_height: 12
  max_blocks_per_image: 12
```

## Bước tiếp theo

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Kiểm tra setup

```bash
python check_ensemble_setup.py
```

### 3. Test engine

```bash
python test_ensemble_engine.py
```

### 4. Start server

```bash
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Test với real data

- Upload template side1 (có Arabic)
- Upload template side2 (có Chinese cuối)
- Kiểm tra preview OCR
- Xem logs để confirm engine="ensemble"

## Tuning

Nếu cần điều chỉnh:

### Tắt verifier (chỉ dùng EasyOCR)

```yaml
verifier:
  enabled: false
```

### Giảm số blocks verify (tăng tốc)

```yaml
verifier:
  max_blocks_per_image: 6
  min_confidence_to_skip: 0.85
```

### Chỉ dùng EasyOCR (không ensemble)

```yaml
engine: easyocr
```

### Rollback về Tesseract

```yaml
engine: tesseract
lang: eng
side_langs:
  side1: ara+eng+fra
  side2: chi_sim+eng+fra
```

## Performance expectations

### Tốc độ (CPU)
- EasyOCR: ~5-8s/ảnh
- KerasOCR verify: ~2-3s/block
- Total: ~10-15s/ảnh (với 2-3 hard blocks)

### Tốc độ (GPU)
- EasyOCR: ~2-3s/ảnh
- KerasOCR verify: ~0.5-1s/block
- Total: ~3-5s/ảnh (với 2-3 hard blocks)

### Memory
- ~1GB RAM (cả 2 models)
- ~2GB VRAM (nếu dùng GPU)

## Rủi ro đã biết

1. **Lần đầu chạy chậm**: EasyOCR + KerasOCR download models (~500MB)
2. **Memory cao**: Cần ~1GB RAM
3. **KerasOCR confidence**: Không chuẩn như EasyOCR, dùng heuristic 0.75
4. **Verifier không phải silver bullet**: Chỉ cải thiện hard blocks, không phải tất cả

## Lợi ích

1. ✓ **Giữ nguyên kiến trúc** - Không phá code hiện tại
2. ✓ **EasyOCR mạnh hơn** - Đặc biệt với Arabic, CJK
3. ✓ **Verifier cải thiện** - Hard blocks được verify lại
4. ✓ **Flexible** - Có thể tắt verifier hoặc rollback
5. ✓ **Config-driven** - Dễ tune và điều chỉnh

## Checklist hoàn thành

- [x] Cập nhật requirements.txt
- [x] Cập nhật configs/ocr.yaml
- [x] Thêm EasyOCREngine
- [x] Thêm KerasOCRVerifier
- [x] Thêm EnsembleOCREngine
- [x] Cập nhật AutoOCREngine
- [x] Tạo check_ensemble_setup.py
- [x] Tạo test_ensemble_engine.py
- [x] Tạo ENSEMBLE_OCR_MIGRATION.md
- [x] Tạo REFACTOR_SUMMARY.md
- [x] Giữ nguyên OCRWorkflow
- [x] Giữ nguyên TemplateService
- [x] Giữ nguyên API routes

## Status

✅ **REFACTOR HOÀN TẤT**

Hệ thống đã sẵn sàng test với Ensemble OCR Engine.
