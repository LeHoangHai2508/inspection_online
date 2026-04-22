# GPU Auto-Detection Summary

## ✅ Đã thêm tính năng auto-detect GPU

### Thay đổi chính

1. **configs/ocr.yaml** - Đổi sang auto-detect:
   ```yaml
   gpu: auto  # Tự động detect GPU
   ```

2. **src/ocr/engine.py** - Thêm 2 helper functions:
   - `_detect_gpu_available()` - Detect GPU từ PyTorch + TensorFlow
   - `_resolve_gpu_setting()` - Parse config: "auto", "true", "false"

3. **Logging** - Thêm log để biết đang dùng GPU hay CPU:
   ```
   [GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
   [Ensemble] Initializing with GPU=True, verifier=True
   [EasyOCR] Running OCR on side1 (GPU=True)
   ```

## Cách hoạt động

### Auto-detect logic

```python
def _detect_gpu_available() -> bool:
    pytorch_gpu = torch.cuda.is_available()
    tensorflow_gpu = len(tf.config.list_physical_devices('GPU')) > 0
    
    # Cả 2 phải có GPU mới return True
    return pytorch_gpu and tensorflow_gpu
```

**Lý do cần cả 2:**
- EasyOCR dùng PyTorch → cần PyTorch CUDA
- KerasOCR dùng TensorFlow → cần TensorFlow GPU
- Nếu chỉ 1 trong 2 có GPU, ensemble vẫn phải dùng CPU

### Config options

| Config | Hành vi |
|--------|---------|
| `gpu: auto` | Tự động detect (khuyến nghị) |
| `gpu: true` | Force GPU (lỗi nếu không có) |
| `gpu: false` | Force CPU (dù có GPU) |

### Logs khi khởi động

**Có GPU:**
```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
[Ensemble] Initializing with GPU=True, verifier=True
[EasyOCR] Initializing with GPU=True, langs=['en', 'fr', ...]
```

**Không có GPU:**
```
[GPU] Auto-detected: PyTorch CUDA=False, TensorFlow GPU=False → Using CPU
[Ensemble] Initializing with GPU=False, verifier=True
[EasyOCR] Initializing with GPU=False, langs=['en', 'fr', ...]
```

**Partial GPU (chỉ 1 trong 2):**
```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=False → Using CPU
```

### Logs khi OCR chạy

```
[EasyOCR] Running OCR on side1 (GPU=True)
[Ensemble] Running on side1 (GPU=True)
[Ensemble] Found 3 hard blocks to verify
[Ensemble] Block 1/3: 'COMPOSITION' → 'COMPOSITION' (conf 0.75 → 0.75)
[Ensemble] Replaced 1 blocks
```

## Test GPU detection

### Script 1: Kiểm tra setup

```bash
python check_ensemble_setup.py
```

Output:
```
✓ PyTorch 2.8.0+cpu installed
  CUDA: Not available (CPU only)

✓ TensorFlow 2.x.x installed
  GPU: Not available (CPU only)
```

### Script 2: Test detection logic

```bash
python test_gpu_detection.py
```

Output:
```
PyTorch CUDA Detection
------------------------------------------------------------
PyTorch version: 2.8.0+cpu
CUDA available: False

TensorFlow GPU Detection
------------------------------------------------------------
TensorFlow version: 2.x.x
GPU devices: 0

Auto-detect GPU Function
------------------------------------------------------------
[GPU] Auto-detected: PyTorch CUDA=False, TensorFlow GPU=False → Using CPU
Result: GPU=Not Available

Summary
------------------------------------------------------------
PyTorch CUDA:     ✗
TensorFlow GPU:   ✗
Auto-detect:      ✓

✗ No GPU available. Ensemble engine will use CPU.

Config recommendation:
  gpu: auto  # Will use CPU automatically
```

## Cài GPU (nếu muốn)

### Bước 1: Kiểm tra NVIDIA GPU

```powershell
nvidia-smi
```

### Bước 2: Cài PyTorch CUDA

```powershell
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Bước 3: Cài TensorFlow GPU

```powershell
pip install tensorflow[and-cuda]
```

### Bước 4: Test lại

```powershell
python test_gpu_detection.py
```

### Bước 5: Restart server

```powershell
python -m uvicorn src.api.main:app --reload
```

Xem log:
```
[GPU] Auto-detected: PyTorch CUDA=True, TensorFlow GPU=True → Using GPU
```

## Không cần sửa config!

**Trước đây:**
- Phải sửa `gpu: true` hoặc `gpu: false` thủ công
- Mỗi máy khác nhau phải config khác nhau
- Dễ quên sửa khi deploy

**Bây giờ:**
- Để `gpu: auto` (mặc định)
- Hệ thống tự động detect
- Cùng 1 config chạy được trên mọi máy

## Files đã thay đổi

1. ✅ `configs/ocr.yaml` - Đổi `gpu: auto`
2. ✅ `src/ocr/engine.py` - Thêm auto-detect logic + logging
3. ✅ `GPU_SETUP.md` - Cập nhật hướng dẫn
4. ✅ `test_gpu_detection.py` - Script test mới
5. ✅ `GPU_AUTO_DETECT_SUMMARY.md` - File này

## Lợi ích

1. ✅ **Tự động** - Không cần config thủ công
2. ✅ **Portable** - Cùng config chạy trên mọi máy
3. ✅ **Transparent** - Log rõ ràng đang dùng GPU hay CPU
4. ✅ **Safe** - Không crash nếu không có GPU
5. ✅ **Flexible** - Vẫn có thể force GPU/CPU nếu cần

## Trả lời câu hỏi của bạn

> "trong máy tôi giả sử là GPU là 0 và cpu là 1 và trên máy người khác thì ngược lại rồi sao"

**Giải pháp:** Hệ thống không dùng device ID (0, 1, ...) mà dùng **boolean check**:

```python
# PyTorch
torch.cuda.is_available()  # True/False

# TensorFlow
len(tf.config.list_physical_devices('GPU')) > 0  # True/False
```

Không quan tâm GPU là device 0 hay 1, chỉ cần biết **có hay không**.

Khi pass `gpu=True` vào EasyOCR/KerasOCR, chúng tự động chọn GPU available.

## Kết luận

✅ **Hoàn tất auto-detect GPU**

- Config: `gpu: auto` (mặc định)
- Logs: Rõ ràng đang dùng GPU hay CPU
- Portable: Chạy được trên mọi máy
- No manual config needed!
