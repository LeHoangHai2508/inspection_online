# Quick Installation Guide

## Bạn chưa cài EasyOCR, KerasOCR, TensorFlow

Từ output của `pip list`, tôi thấy bạn chỉ có:
- ✓ PaddleOCR
- ✓ OpenCV
- ✓ Pillow

Nhưng thiếu:
- ✗ PyTorch
- ✗ EasyOCR
- ✗ KerasOCR
- ✗ TensorFlow

## Cài đặt nhanh (CPU version)

### Option 1: Dùng script tự động

```powershell
python install_ensemble_deps.py
```

### Option 2: Cài thủ công

```powershell
# Cài EasyOCR (sẽ tự động cài PyTorch)
pip install easyocr

# Cài KerasOCR
pip install keras-ocr

# Cài TensorFlow
pip install tensorflow
```

## Cài đặt GPU version (nếu có NVIDIA GPU)

### Bước 1: Kiểm tra GPU

```powershell
nvidia-smi
```

Nếu có GPU, tiếp tục:

### Bước 2: Cài PyTorch GPU

```powershell
# CUDA 11.8 (khuyến nghị)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Bước 3: Cài EasyOCR

```powershell
pip install easyocr
```

### Bước 4: Cài TensorFlow GPU

```powershell
pip install tensorflow[and-cuda]
```

### Bước 5: Cài KerasOCR

```powershell
pip install keras-ocr
```

## Kiểm tra sau khi cài

```powershell
python check_ensemble_setup.py
```

Bạn sẽ thấy:

```
✓ OpenCV installed
✓ Pillow installed
✓ PyTorch installed
✓ EasyOCR installed
✓ TensorFlow installed
✓ KerasOCR installed
```

## Nếu gặp lỗi

### Lỗi: Microsoft Visual C++ required

Download và cài: https://aka.ms/vs/17/release/vc_redist.x64.exe

### Lỗi: Cannot install torch

Thử cài từng bước:

```powershell
pip install torch
pip install torchvision
pip install torchaudio
pip install easyocr
```

### Lỗi: TensorFlow không cài được

Thử version cũ hơn:

```powershell
pip install tensorflow==2.15.0
```

## Ước tính thời gian cài

- **EasyOCR + PyTorch**: ~500MB, 5-10 phút
- **TensorFlow**: ~400MB, 3-5 phút
- **KerasOCR**: ~50MB, 1-2 phút

**Total**: ~1GB download, 10-15 phút

## Sau khi cài xong

```powershell
# Test
python check_ensemble_setup.py

# Test GPU detection
python test_gpu_detection.py

# Start server
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

## Nếu không muốn cài Ensemble

Bạn vẫn có thể dùng PaddleOCR hoặc Tesseract:

**configs/ocr.yaml:**
```yaml
engine: paddleocr  # Hoặc tesseract
```

Không cần cài thêm gì.
