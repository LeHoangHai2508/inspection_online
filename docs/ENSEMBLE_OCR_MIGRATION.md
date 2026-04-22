# Migration Guide: Ensemble OCR Engine

## Tổng quan

Refactor này thay thế Tesseract bằng **Ensemble OCR Engine**:
- **EasyOCR** làm OCR chính (primary)
- **KerasOCR** làm verifier cho hard blocks
- Giữ nguyên kiến trúc `OCRDocument`, `OCRWorkflow`, `TemplateService`

## Kiến trúc mới

```
Ảnh input
  ↓
EasyOCR đọc toàn ảnh
  ↓
Tạo OCRBlock ban đầu
  ↓
Chọn hard blocks (confidence thấp, Arabic, CJK cuối ảnh)
  ↓
Crop từng hard block
  ↓
KerasOCR verify lại block đó
  ↓
Nếu text mới tốt hơn → thay block cũ
  ↓
Render lại raw_text
  ↓
Trả OCRDocument
```

## Lợi ích

1. **EasyOCR mạnh hơn Tesseract** cho multi-language (Arabic, CJK)
2. **KerasOCR verify** giúp cải thiện hard blocks
3. **Giữ nguyên interface** - không phá code hiện tại
4. **Flexible config** - có thể tắt verifier hoặc chỉ dùng EasyOCR

## Cài đặt

### Bước 1: Cài thư viện

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# hoặc
.venv\Scripts\activate  # Windows

# Cài đặt
pip install easyocr keras-ocr tensorflow
```

### Bước 2: Kiểm tra cài đặt

```bash
python check_ensemble_setup.py
```

### Bước 3: Cập nhật config

File `configs/ocr.yaml` đã được cập nhật:

```yaml
engine: ensemble  # EasyOCR primary + KerasOCR verifier

easyocr_langs:
  - en
  - fr
  - de
  - it
  - es
  - pt
  - ru
  - ar
  - ch_sim
  - ch_tra
  - ja
  - ko
  - th
  - vi

verifier:
  enabled: true
  min_confidence_to_skip: 0.82
  min_block_width: 20
  min_block_height: 12
  max_blocks_per_image: 12

strict_real_ocr: true

providers:
  - ensemble
  - easyocr
  - mock
```

## Cấu hình

### Engine options

- `engine: ensemble` - EasyOCR + KerasOCR verifier
- `engine: easyocr` - Chỉ EasyOCR (không verify)
- `engine: auto` - Tự động chọn: ensemble → easyocr → paddleocr → tesseract → mock

### EasyOCR languages

Danh sách ngôn ngữ EasyOCR hỗ trợ. Xem đầy đủ tại: https://www.jaided.ai/easyocr/

### Verifier config

- `enabled: true/false` - Bật/tắt KerasOCR verifier
- `min_confidence_to_skip: 0.82` - Block có confidence >= 0.82 sẽ không verify
- `min_block_width: 20` - Block nhỏ hơn 20px width sẽ không verify
- `min_block_height: 12` - Block nhỏ hơn 12px height sẽ không verify
- `max_blocks_per_image: 12` - Tối đa 12 blocks được verify mỗi ảnh

## Hard blocks detection

Hệ thống tự động chọn hard blocks để verify:

1. **Confidence thấp**: `confidence < min_confidence_to_skip`
2. **Side1 có Arabic**: Blocks chứa ký tự Arabic (U+0600 - U+06FF)
3. **Side2 vùng cuối**: Blocks ở 38% cuối ảnh (dễ lỗi CJK)

## Testing

### Test cơ bản

```bash
# Start server
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000

# Upload template qua UI
# Kiểm tra preview OCR
```

### Test cases quan trọng

1. **Side1 Arabic**: Kiểm tra text Arabic đọc đúng
2. **Side2 Chinese cuối**: Kiểm tra CJK ở cuối nhãn
3. **Footer VERSO**: Kiểm tra không dính text "VERSO 2"

## Performance

### Tốc độ

- **EasyOCR**: ~2-3s/ảnh (GPU), ~5-8s/ảnh (CPU)
- **KerasOCR verify**: ~0.5-1s/block (GPU), ~2-3s/block (CPU)
- **Total**: Phụ thuộc số hard blocks (thường 2-5 blocks)

### Memory

- **EasyOCR model**: ~500MB RAM
- **KerasOCR model**: ~300MB RAM
- **Total**: ~1GB RAM khi cả 2 engine load

### GPU

Để dùng GPU:

1. **PyTorch CUDA** (cho EasyOCR):
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

2. **TensorFlow GPU** (cho KerasOCR):
   ```bash
   pip install tensorflow[and-cuda]
   ```

## Troubleshooting

### EasyOCR không load được model

```
Error: Cannot download model
```

**Fix**: Kiểm tra internet connection. EasyOCR tự động download models lần đầu.

### KerasOCR chậm

```
Verifier takes too long
```

**Fix**: 
- Giảm `max_blocks_per_image` xuống 6-8
- Tăng `min_confidence_to_skip` lên 0.85-0.90
- Hoặc tắt verifier: `verifier.enabled: false`

### Out of memory

```
CUDA out of memory / RAM exhausted
```

**Fix**:
- Tắt GPU: Sửa `gpu=False` trong `EasyOCREngine.__init__`
- Hoặc chỉ dùng EasyOCR: `engine: easyocr`

### Import error

```
ModuleNotFoundError: No module named 'easyocr'
```

**Fix**: Cài lại dependencies:
```bash
pip install -r requirements.txt
```

## Rollback

Nếu cần quay lại Tesseract:

1. Sửa `configs/ocr.yaml`:
   ```yaml
   engine: tesseract
   lang: eng
   side_langs:
     side1: ara+eng+fra
     side2: chi_sim+eng+fra
   ```

2. Restart server

## Code changes summary

### Files modified

1. `requirements.txt` - Thêm easyocr, keras-ocr, tensorflow
2. `configs/ocr.yaml` - Đổi config sang ensemble
3. `src/ocr/engine.py` - Thêm EasyOCREngine, KerasOCRVerifier, EnsembleOCREngine

### Files unchanged

- `src/ocr/workflow.py` - Không đổi
- `src/ocr/service.py` - Không đổi
- `src/api/routes/` - Không đổi
- `src/domain/models.py` - Không đổi

## Next steps

1. **Test thoroughly** với real templates
2. **Tune verifier config** dựa trên kết quả
3. **Monitor performance** và memory usage
4. **Consider GPU** nếu cần tăng tốc

## Support

Nếu gặp vấn đề:

1. Chạy `python check_ensemble_setup.py`
2. Kiểm tra logs server
3. Test với `engine: easyocr` trước (không verifier)
4. Rollback về Tesseract nếu cần
