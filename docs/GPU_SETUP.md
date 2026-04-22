# GPU Setup Guide

## Auto-detect GPU (Khuyến nghị)

Hệ thống **tự động phát hiện GPU** khi khởi động. Không cần config thủ công!

### Config mặc định (configs/ocr.yaml)

```yaml
# GPU settings
gpu: auto  # Tự động detect GPU
```

Khi server khởi động, bạn sẽ thấy log:

```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
[Ensemble] Initializing with GPU=True, verifier=True
[EasyOCR] Initializing with GPU=True, langs=['en', 'fr', ...]
```

Hoặc nếu không có GPU:

```
[GPU] Auto-detected: PyTorch CUDA=False, TensorFlow GPU=False → Using CPU
[Ensemble] Initializing with GPU=False, verifier=True
[EasyOCR] Initializing with GPU=False, langs=['en', 'fr', ...]
```

## Vấn đề hiện tại

Bạn đang dùng **PyTorch CPU** (`2.8.0+cpu`), không có CUDA support.

```
✓ PyTorch 2.8.0+cpu installed
CUDA: Not available (CPU only)
```

Hệ thống sẽ **tự động dùng CPU** khi không detect được GPU.

## Để chạy GPU

### Bước 1: Kiểm tra GPU

```powershell
# Kiểm tra NVIDIA GPU
nvidia-smi
```

Nếu không có lệnh `nvidia-smi` hoặc không thấy GPU, bạn cần:
1. Cài NVIDIA GPU driver
2. Cài CUDA Toolkit

### Bước 2: Cài PyTorch với CUDA

**Gỡ PyTorch CPU hiện tại:**

```powershell
pip uninstall torch torchvision torchaudio
```

**Cài PyTorch GPU:**

Chọn phiên bản CUDA phù hợp với GPU của bạn:

#### CUDA 11.8 (khuyến nghị cho GPU cũ hơn)

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### CUDA 12.1 (cho GPU mới)

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### CUDA 12.4 (mới nhất)

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### Bước 3: Cài TensorFlow GPU (cho KerasOCR)

```powershell
pip uninstall tensorflow
pip install tensorflow[and-cuda]
```

Hoặc nếu gặp lỗi:

```powershell
pip install tensorflow-gpu
```

### Bước 4: Kiểm tra lại

```powershell
python check_ensemble_setup.py
```

Bạn sẽ thấy:

```
✓ PyTorch 2.x.x+cu118 installed
  CUDA available: NVIDIA GeForce RTX 3060

✓ TensorFlow 2.x.x installed
  GPU available: 1 device(s)
    - /physical_device:GPU:0
```

### Bước 5: Kiểm tra auto-detect

Restart server và xem log:

```powershell
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Bạn sẽ thấy:

```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
[Ensemble] Initializing with GPU=True, verifier=True
```

✅ **Không cần sửa config!** Hệ thống tự động dùng GPU.

## Force GPU hoặc CPU (Optional)

Nếu muốn force, sửa `configs/ocr.yaml`:

```yaml
# GPU settings
gpu: true   # Force GPU (lỗi nếu không có GPU)
# hoặc
gpu: false  # Force CPU (dù có GPU)
# hoặc
gpu: auto   # Auto-detect (khuyến nghị)
```

## Nếu không có GPU

**Không cần làm gì!** Hệ thống tự động dùng CPU.

```yaml
# GPU settings
gpu: auto  # Tự động detect → sẽ dùng CPU nếu không có GPU
```

Server vẫn chạy bình thường, chỉ chậm hơn.

## Performance so sánh

### CPU (hiện tại)
- EasyOCR: ~5-8s/ảnh
- KerasOCR verify: ~2-3s/block
- **Total: ~10-15s/ảnh**

### GPU (sau khi cài)
- EasyOCR: ~2-3s/ảnh
- KerasOCR verify: ~0.5-1s/block
- **Total: ~3-5s/ảnh**

**Tăng tốc: 3-4x**

## Troubleshooting

### Lỗi: CUDA out of memory

```yaml
gpu: false  # Quay lại CPU
```

Hoặc giảm số blocks verify:

```yaml
verifier:
  max_blocks_per_image: 6
```

### Lỗi: Could not load dynamic library 'cudart64_110.dll'

Cài CUDA Toolkit phù hợp với PyTorch version:
- PyTorch cu118 → CUDA 11.8
- PyTorch cu121 → CUDA 12.1

Download: https://developer.nvidia.com/cuda-downloads

### Lỗi: TensorFlow không thấy GPU

```powershell
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

Nếu trả về `[]`, cài lại:

```powershell
pip install tensorflow[and-cuda] --upgrade
```

## Kiểm tra GPU đang được dùng

### Cách 1: Xem log khi server khởi động

```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
[Ensemble] Initializing with GPU=True, verifier=True
[EasyOCR] Initializing with GPU=True, langs=[...]
```

### Cách 2: Xem log khi OCR chạy

```
[EasyOCR] Running OCR on side1 (GPU=True)
[Ensemble] Running on side1 (GPU=True)
```

### Cách 3: Kiểm tra thủ công

```powershell
# PyTorch
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# TensorFlow
python -c "import tensorflow as tf; print(f'GPU: {len(tf.config.list_physical_devices(\"GPU\"))}')"
```

### Cách 4: Xem GPU usage (nếu có NVIDIA GPU)

```powershell
nvidia-smi
```

Khi OCR đang chạy, bạn sẽ thấy process `python.exe` dùng GPU memory.

## Tóm tắt

| Bước | Lệnh | Mục đích |
|------|------|----------|
| 1 | `nvidia-smi` | Kiểm tra GPU |
| 2 | `pip install torch --index-url ...cu118` | Cài PyTorch GPU |
| 3 | `pip install tensorflow[and-cuda]` | Cài TensorFlow GPU |
| 4 | `python check_ensemble_setup.py` | Kiểm tra |
| 5 | Restart server | Hệ thống tự động detect GPU |

## Config file

**configs/ocr.yaml** - Không cần sửa, để mặc định:

```yaml
engine: ensemble

# GPU settings - TỰ ĐỘNG DETECT
gpu: auto   # auto = tự động, true = force GPU, false = force CPU

easyocr_langs:
  - en
  - fr
  # ...
```

## Logs quan trọng

Khi server khởi động, xem log để biết đang dùng GPU hay CPU:

```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
```

Hoặc:

```
[GPU] Auto-detected: PyTorch CUDA=False, TensorFlow GPU=False → Using CPU
```

**Không cần config thủ công!** Hệ thống tự động chọn GPU nếu có, CPU nếu không.
