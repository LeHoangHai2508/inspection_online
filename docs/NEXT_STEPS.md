# Next Steps - Cài đặt Ensemble OCR

## Tình trạng hiện tại

✓ **Đã hoàn tất refactor code**
- Engine mới: EasyOCR + KerasOCR
- Auto-detect GPU
- Config: `configs/ocr.yaml`

✗ **Chưa cài dependencies**
- PyTorch
- EasyOCR
- TensorFlow
- KerasOCR

## Lựa chọn của bạn

### Option 1: Cài Ensemble OCR (khuyến nghị)

**Ưu điểm:**
- Mạnh hơn Tesseract/PaddleOCR
- Hỗ trợ tốt Arabic, CJK
- Verifier cải thiện hard blocks

**Nhược điểm:**
- Cần cài thêm ~1GB packages
- Chậm hơn nếu không có GPU

**Cài đặt:**

```powershell
# CPU version (nhanh, đủ dùng)
pip install easyocr keras-ocr tensorflow

# Hoặc dùng script tự động
python install_ensemble_deps.py
```

**Thời gian:** 10-15 phút

### Option 2: Dùng PaddleOCR (đã có sẵn)

**Ưu điểm:**
- Đã cài sẵn
- Không cần cài thêm
- Chạy ngay

**Nhược điểm:**
- Không mạnh bằng Ensemble
- Không có verifier

**Cách dùng:**

Sửa `configs/ocr.yaml`:
```yaml
engine: paddleocr  # Thay vì ensemble
```

Restart server:
```powershell
python -m uvicorn src.api.main:app --reload
```

### Option 3: Dùng Tesseract (nếu đã cài)

**Cách dùng:**

Sửa `configs/ocr.yaml`:
```yaml
engine: tesseract
lang: eng
side_langs:
  side1: ara+eng+fra
  side2: chi_sim+eng+fra
```

## Khuyến nghị

### Nếu bạn muốn test ngay

→ **Dùng PaddleOCR** (Option 2)

Sửa config và restart server. Không cần cài gì thêm.

### Nếu bạn muốn OCR tốt nhất

→ **Cài Ensemble** (Option 1)

Chạy:
```powershell
pip install easyocr keras-ocr tensorflow
```

Đợi 10-15 phút, sau đó restart server.

## Cài Ensemble OCR - Chi tiết

### Bước 1: Cài packages

```powershell
# Activate venv (nếu chưa)
.venv\Scripts\activate

# Cài dependencies
pip install easyocr keras-ocr tensorflow
```

### Bước 2: Kiểm tra

```powershell
python check_ensemble_setup.py
```

Bạn sẽ thấy:
```
✓ PyTorch installed
✓ EasyOCR installed
✓ TensorFlow installed
✓ KerasOCR installed
```

### Bước 3: Test GPU detection

```powershell
python test_gpu_detection.py
```

Output:
```
[GPU] Auto-detected: PyTorch CUDA=False, TensorFlow GPU=False → Using CPU
```

### Bước 4: Start server

```powershell
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Xem log:
```
[GPU] Auto-detected: ... → Using CPU
[Ensemble] Initializing with GPU=False, verifier=True
[EasyOCR] Initializing with GPU=False, langs=[...]
```

### Bước 5: Test OCR

Upload template qua UI và kiểm tra preview.

## GPU Support (Optional)

Nếu có NVIDIA GPU và muốn tăng tốc:

```powershell
# Gỡ PyTorch CPU
pip uninstall torch torchvision torchaudio

# Cài PyTorch GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Cài TensorFlow GPU
pip uninstall tensorflow
pip install tensorflow[and-cuda]
```

Restart server, log sẽ hiện:
```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
```

## Troubleshooting

### Lỗi: pip install chậm

Dùng mirror:
```powershell
pip install easyocr -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Lỗi: Out of memory khi cài

Cài từng package:
```powershell
pip install torch
pip install easyocr
pip install tensorflow
pip install keras-ocr
```

### Lỗi: Microsoft Visual C++ required

Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

## Summary

| Option | Cài đặt | Thời gian | Chất lượng OCR |
|--------|---------|-----------|----------------|
| **Ensemble** | Cần cài | 10-15 phút | ⭐⭐⭐⭐⭐ |
| **PaddleOCR** | Đã có | 0 phút | ⭐⭐⭐⭐ |
| **Tesseract** | Nếu có | 0 phút | ⭐⭐⭐ |

## Quyết định của bạn?

1. **Test ngay với PaddleOCR** → Sửa config, restart
2. **Cài Ensemble để OCR tốt hơn** → `pip install easyocr keras-ocr tensorflow`
3. **Dùng Tesseract** → Sửa config

Chọn option nào cũng được, code đã sẵn sàng!
