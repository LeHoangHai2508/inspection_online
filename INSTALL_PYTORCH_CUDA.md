# Hướng dẫn cài PyTorch với CUDA support

## Vấn đề hiện tại

Bạn đang dùng **PyTorch CPU-only version** (`torch 2.8.0+cpu`), nên không thể dùng GPU.

```
✗ PyTorch 2.8.0+cpu installed
CUDA: Not available (CPU only)
```

## Giải pháp: Cài lại PyTorch với CUDA

### Bước 1: Kiểm tra máy có GPU không

```bash
nvidia-smi
```

Nếu lệnh này chạy được và hiện thông tin GPU → máy có NVIDIA GPU.

Nếu lỗi → máy không có GPU hoặc driver chưa cài.

### Bước 2: Gỡ PyTorch CPU-only

```bash
pip uninstall torch torchvision torchaudio
```

### Bước 3: Cài PyTorch với CUDA

**Cho CUDA 11.8** (khuyến nghị cho hầu hết GPU):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Cho CUDA 12.1** (nếu driver mới):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Kiểm tra CUDA version của driver:**

```bash
nvidia-smi
```

Dòng đầu tiên sẽ hiện `CUDA Version: 12.x` hoặc `11.x`.

### Bước 4: Kiểm tra lại

```bash
python check_gpu_real.py
```

Nên thấy:

```
✓ PyTorch 2.x.x+cu118 with CUDA support
  CUDA version: 11.8
  GPU count: 1
  GPU 0: NVIDIA GeForce RTX 3060
```

### Bước 5: Chạy lại server

```bash
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Log nên hiện:

```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
[EasyOCR] Initializing with GPU=True, langs=[...]
```

## Nếu không có GPU

Nếu máy không có NVIDIA GPU, sửa `configs/ocr.yaml`:

```yaml
gpu: false
```

Hoặc dùng engine khác không cần GPU:

```yaml
engine: paddleocr  # hoặc tesseract
```

## Tham khảo

- PyTorch installation: https://pytorch.org/get-started/locally/
- CUDA compatibility: https://pytorch.org/get-started/previous-versions/
