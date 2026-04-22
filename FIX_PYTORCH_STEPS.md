# Fix PyTorch CUDA trong Virtual Environment

## Vấn đề hiện tại

Server báo:
```
[EasyOCR] Initializing with GPU=True
Neither CUDA nor MPS are available - defaulting to CPU
```

→ PyTorch trong `.venv` vẫn là **CPU-only version**

## Nguyên nhân

Có thể bạn đã cài PyTorch CUDA vào **global Python** thay vì vào `.venv`.

## Giải pháp: Cài lại PyTorch CUDA vào .venv

### Bước 1: Stop server (Ctrl+C)

### Bước 2: Activate venv và kiểm tra

```powershell
# Activate venv (phải thấy (.venv) ở đầu dòng)
.venv\Scripts\activate

# Kiểm tra PyTorch hiện tại
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')"
```

Nếu thấy:
```
PyTorch: 2.8.0+cpu
CUDA: False
```

→ Cần cài lại

### Bước 3: Gỡ PyTorch CPU-only

```powershell
pip uninstall -y torch torchvision torchaudio
```

### Bước 4: Cài PyTorch CUDA 12.1

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Lưu ý:** Dùng cu121 vì driver của bạn là CUDA 12.5 (tương thích ngược)

### Bước 5: Kiểm tra lại

```powershell
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Phải thấy:
```
PyTorch: 2.x.x+cu121
CUDA: True
GPU: NVIDIA GeForce GTX 1650
```

### Bước 6: Chạy lại server

```powershell
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Log phải hiện:
```
[EasyOCR] Initializing with GPU=True
CUDA is available
```

Không còn dòng "Neither CUDA nor MPS are available"

## Nếu vẫn lỗi

### Option A: Kiểm tra pip đang trỏ đâu

```powershell
where pip
```

Phải thấy:
```
C:\Users\Admin\Desktop\project\garment_label_inspection_ver\.venv\Scripts\pip.exe
```

Nếu không → activate lại venv

### Option B: Dùng python -m pip

```powershell
python -m pip uninstall -y torch torchvision torchaudio
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Option C: Nếu không có GPU hoặc không muốn dùng GPU

Sửa `configs/ocr.yaml`:
```yaml
gpu: false
```

Hoặc dùng engine khác:
```yaml
engine: paddleocr  # hoặc tesseract
```

## Kiểm tra cuối cùng

Sau khi cài xong, chạy:

```powershell
python fix_pytorch_venv.py
```

Phải thấy:
```
✓ Đang ở virtual environment
✓ PyTorch CUDA OK!
  CUDA version: 12.1
  GPU count: 1
  GPU 0: NVIDIA GeForce GTX 1650
```
