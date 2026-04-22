# Garment Label Inspection

Hệ thống AI kiểm tra tem quần áo 2 mặt theo luồng:

```
Upload template → OCR full → Review / Approve
→ Side1 capture → Compare → Confirm
→ Side2 capture → Compare → Overall → IoT
```

---

## Yêu cầu hệ thống

### Phần cứng
- **CPU**: Intel Core i5 hoặc tương đương
- **RAM**: 8GB+ (khuyến nghị 16GB nếu dùng GPU)
- **GPU** (tuỳ chọn): NVIDIA GPU với CUDA support (GTX 1650+)
  - Driver NVIDIA phiên bản mới nhất
  - CUDA 11.8 hoặc 12.x

### Phần mềm
- **Python 3.9+** (khuyến nghị Python 3.9 hoặc 3.10)
- **Windows 10/11** hoặc Linux
- **Git** (để clone repository)

### OCR Engine (chọn 1 trong 3)
1. **EasyOCR + KerasOCR** (Ensemble - khuyến nghị, cần GPU)
2. **PaddleOCR** (nhanh, hỗ trợ nhiều ngôn ngữ)
3. **Tesseract** (miễn phí, không cần GPU)

---

## Hướng dẫn cài đặt chi tiết

### Bước 1: Clone repository

```bash
git clone <repository-url>
cd garment_label_inspection_ver
```

### Bước 2: Tạo virtual environment

**Windows:**
```powershell
# Cho phép chạy script PowerShell (chỉ cần làm 1 lần)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Tạo virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Lưu ý quan trọng:**
- Sau khi activate, bạn phải thấy `(.venv)` ở đầu dòng terminal
- Mọi lệnh `pip install` và `python` sau này phải chạy trong venv này
- Nếu đóng terminal, cần activate lại: `.venv\Scripts\activate`

### Bước 3: Cài đặt dependencies cơ bản

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 4: Chọn và cài đặt OCR Engine

#### Option A: EasyOCR + KerasOCR (Ensemble - khuyến nghị)

**Ưu điểm:**
- Độ chính xác cao nhất
- Hỗ trợ nhiều ngôn ngữ (Arabic, CJK, Latin)
- Tự động verify các block khó

**Nhược điểm:**
- Cần GPU NVIDIA (GTX 1650+)
- Cài đặt phức tạp hơn
- Tốn RAM nhiều hơn

**Cài đặt:**

1. **Kiểm tra GPU:**
```bash
nvidia-smi
```

Nếu lệnh này chạy được và hiện thông tin GPU → máy có NVIDIA GPU, tiếp tục bước 2.

Nếu lỗi → máy không có GPU, chọn Option B hoặc C.

2. **Cài PyTorch với CUDA:**

Kiểm tra CUDA version từ `nvidia-smi` (dòng đầu tiên):
- Nếu `CUDA Version: 12.x` → dùng cu121
- Nếu `CUDA Version: 11.x` → dùng cu118

```bash
# Cho CUDA 12.x (khuyến nghị)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Hoặc cho CUDA 11.x
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

3. **Cài TensorFlow GPU:**
```bash
pip install tensorflow
```

4. **Cài EasyOCR và KerasOCR:**
```bash
pip install easyocr keras-ocr
```

5. **Kiểm tra cài đặt:**
```bash
python check_gpu_real.py
```

Phải thấy:
```
✓ NVIDIA GPU detected
✓ PyTorch with CUDA support
✓ TensorFlow with GPU support
✓ GPU sẵn sàng cho EasyOCR + KerasOCR!
```

6. **Cấu hình:**

File `configs/ocr.yaml` đã được cấu hình sẵn:
```yaml
engine: ensemble
gpu: true
```

#### Option B: PaddleOCR (không cần GPU)

**Ưu điểm:**
- Nhanh, nhẹ
- Không cần GPU
- Hỗ trợ nhiều ngôn ngữ

**Cài đặt:**
```bash
pip install paddlepaddle paddleocr
```

**Cấu hình:**

Sửa `configs/ocr.yaml`:
```yaml
engine: paddleocr
gpu: false
```

#### Option C: Tesseract (miễn phí, không cần GPU)

**Ưu điểm:**
- Miễn phí, mã nguồn mở
- Không cần GPU
- Nhẹ nhất

**Nhược điểm:**
- Độ chính xác thấp hơn
- Cần cài thêm language packs

**Cài đặt:**

1. **Cài Tesseract:**
   - Windows: Download từ https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt install tesseract-ocr`
   - macOS: `brew install tesseract`

2. **Cài language packs:**
   - Windows: Chọn trong installer
   - Linux: `sudo apt install tesseract-ocr-eng tesseract-ocr-chi-sim tesseract-ocr-ara`

3. **Cài Python wrapper:**
```bash
pip install pytesseract
```

**Cấu hình:**

Sửa `configs/ocr.yaml`:
```yaml
engine: tesseract
gpu: false
```

### Bước 5: Khởi tạo database

```bash
python scripts/init_sqlite.py
```

Hoặc thủ công:
```bash
python -c "from src.db.sqlite import initialize_database; initialize_database('data/sqlite/inspection.db', 'src/db/schema.sql')"
```

### Bước 6: Kiểm tra cài đặt

```bash
# Kiểm tra OCR engine
python docs/check_ocr_setup.py

# Nếu dùng GPU, kiểm tra GPU
python check_gpu_real.py
```

---

## Chạy ứng dụng

### Chạy Web UI + API server (khuyến nghị)

```bash
# Đảm bảo đang ở virtual environment (thấy (.venv) ở đầu dòng)
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Mở trình duyệt tại: **http://127.0.0.1:8000**

API documentation: **http://127.0.0.1:8000/docs**

---

## Khởi tạo database

```bash
python scripts/init_sqlite.py
```

Hoặc thủ công:

```bash
python -c "from src.db.sqlite import initialize_database; initialize_database('data/sqlite/inspection.db', 'src/db/schema.sql')"
```

---

## Các trang Web UI

| URL | Mục đích |
|---|---|
| `/` | Dashboard — KPI + lịch sử gần nhất |
| `/templates/upload` | Upload template mới |
| `/templates/{id}/review` | Review và approve template |
| `/inspect/side1` | Inspect side 1 (upload hoặc live camera) |
| `/inspect/{id}/confirm-side2` | Xác nhận chuyển mặt 2 |
| `/inspect/side2` | Inspect side 2 |
| `/result/{id}` | Xem kết quả tổng hợp |
| `/history` | Lịch sử kiểm tra với bộ lọc |

---

### Chạy UI (Streamlit - tuỳ chọn)

```bash
streamlit run src/ui/dashboard_app.py
```

Mở trình duyệt tại: **http://localhost:8501**

Các trang:

| Trang | Mục đích |
|---|---|
| 01 Live Monitor | Runtime inspection side1 / side2 |
| 02 History | Tra cứu lịch sử kiểm tra |
| 03 Templates | Upload, review, approve template |
| 04 Bad Cases | Xem lại các case NG / UNCERTAIN |
| 05 Statistics | Thống kê tổng hợp KPI |

---

## Xử lý lỗi thường gặp

### Lỗi 1: "Neither CUDA nor MPS are available - defaulting to CPU"

**Nguyên nhân:** PyTorch không detect được GPU

**Giải pháp:**

1. Kiểm tra GPU:
```bash
nvidia-smi
```

2. Kiểm tra PyTorch trong venv:
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')"
```

3. Nếu thấy `PyTorch: 2.x.x+cpu` → cần cài lại:
```bash
# Gỡ PyTorch CPU-only
pip uninstall -y torch torchvision torchaudio

# Cài PyTorch CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Kiểm tra lại
python check_gpu_real.py
```

4. Restart server

### Lỗi 2: "Thai is only compatible with English" hoặc "Chinese_tra is only compatible with English"

**Nguyên nhân:** EasyOCR yêu cầu một số ngôn ngữ phải đi kèm English

**Giải pháp:** File `configs/ocr.yaml` đã được cấu hình để tránh lỗi này. Nếu vẫn gặp, kiểm tra:

```yaml
easyocr_langs:
  - en
  - fr
  - de
  - es
  - pt
  - ru
  - ar
  - ch_sim
  - ja
  - ko
```

Không dùng: `th`, `ch_tra`, `vi` (trừ khi thêm `en` vào đầu list)

### Lỗi 3: "pip install" cài vào global Python thay vì venv

**Nguyên nhân:** Chưa activate virtual environment

**Giải pháp:**

1. Kiểm tra có `(.venv)` ở đầu dòng terminal không
2. Nếu không, activate lại:
```bash
.venv\Scripts\activate
```

3. Kiểm tra pip đang trỏ đâu:
```bash
where pip
```

Phải thấy: `C:\...\garment_label_inspection_ver\.venv\Scripts\pip.exe`

4. Nếu vẫn sai, dùng:
```bash
python -m pip install <package>
```

### Lỗi 4: "numpy version conflict" hoặc "opencv-python requires numpy >= 2.0"

**Nguyên nhân:** Conflict giữa KerasOCR (cần numpy < 2.0) và opencv-python mới (cần numpy >= 2.0)

**Giải pháp:**

Option A: Dùng numpy 1.26.4 và ignore warning
```bash
pip install "numpy<2.0"
```

Option B: Không dùng KerasOCR verifier
```yaml
# configs/ocr.yaml
verifier:
  enabled: false
```

Option C: Chuyển sang PaddleOCR
```yaml
# configs/ocr.yaml
engine: paddleocr
gpu: false
```

### Lỗi 5: "strict_real_ocr=True but no real OCR backend is available"

**Nguyên nhân:** Không có OCR engine nào được cài đặt

**Giải pháp:**

Option A: Cài OCR engine (xem Bước 4 ở trên)

Option B: Tắt strict mode (chỉ dùng cho dev/test)
```yaml
# configs/ocr.yaml
strict_real_ocr: false
```

### Lỗi 6: Server không chạy được hoặc "Address already in use"

**Nguyên nhân:** Port 8000 đang được dùng bởi process khác

**Giải pháp:**

Option A: Đổi port
```bash
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8001
```

Option B: Kill process đang dùng port 8000
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux
lsof -ti:8000 | xargs kill -9
```

### Lỗi 7: "ModuleNotFoundError: No module named 'xxx'"

**Nguyên nhân:** Thiếu dependencies

**Giải pháp:**
```bash
# Cài lại tất cả dependencies
pip install -r requirements.txt

# Hoặc cài package cụ thể
pip install <package-name>
```

### Lỗi 8: Virtual environment không activate được trên Windows

**Nguyên nhân:** PowerShell execution policy

**Giải pháp:**
```powershell
# Chạy lệnh này trước khi activate
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Sau đó activate
.venv\Scripts\activate
```

---

## Kiểm tra hệ thống

### Kiểm tra GPU (nếu dùng Ensemble)

```bash
python check_gpu_real.py
```

Kết quả mong đợi:
```
✓ NVIDIA GPU detected
✓ PyTorch with CUDA support
✓ TensorFlow with GPU support
✓ GPU sẵn sàng cho EasyOCR + KerasOCR!
```

### Kiểm tra OCR engine

```bash
python docs/check_ocr_setup.py
```

### Test OCR với ảnh mẫu

```bash
# Tạo file test_ocr_quick.py
python -c "
from src.ocr.engine import AutoOCREngine
from src.domain.models import TemplateUploadFile
from src.domain.enums import InspectionSide

engine = AutoOCREngine()
with open('path/to/test_image.jpg', 'rb') as f:
    file = TemplateUploadFile(
        filename='test.jpg',
        content=f.read(),
        media_type='image/jpeg'
    )
    result = engine.run(InspectionSide.SIDE1, file)
    print(f'Engine: {result.engine_name}')
    print(f'Text: {result.raw_text[:100]}...')
    print(f'Blocks: {len(result.blocks)}')
"
```

---

## Luồng sử dụng cơ bản

### 1. Upload và approve template

Vào trang **03 Templates**:

1. Điền Template Name, Product Code
2. Upload ảnh side1 và side2
3. Nhấn **Upload** → hệ thống OCR full và sinh `template_id`
4. Nhấn **Load Preview** để xem OCR text và danh sách field
5. Chỉnh sửa field trong bảng form (field_name, expected_value, compare_type, priority)
6. Nhấn **Save Fields**
7. Nhấn **Approve Template** → template sẵn sàng dùng cho runtime

### 2. Runtime inspection

Vào trang **01 Live Monitor**:

1. Nhập Template ID đã approve
2. Nhập Scan Job ID (ví dụ: `JOB_001`)
3. Chọn mode:
   - **Upload mode** (mặc định): upload ảnh cam1/cam2 để test
   - **Live Camera mode**: bật toggle → hệ thống tự chụp từ camera thật
4. Nhấn **Inspect Side1** → xem kết quả, lỗi, ảnh annotate
5. Nhấn **Xác nhận chuyển mặt 2**
6. Nhấn **Inspect Side2**
7. Nhấn **Load Final Result** → xem overall status và operator action

---

## Cấu hình

### `configs/app.yaml`

```yaml
env: local   # local | dev | prod
```

- `local` / `dev`: OCR fallback về mock nếu không có backend thật
- `prod`: bắt buộc có PaddleOCR hoặc Tesseract, app sẽ fail khi start nếu thiếu

### `configs/ocr.yaml`

```yaml
engine: auto          # auto | paddleocr | tesseract | mock
strict_real_ocr: false  # true = cấm fallback mock
```

Để ép dùng OCR thật trong production:

```yaml
strict_real_ocr: true
```

### `configs/camera.yaml`

Cấu hình ROI crop cố định cho từng mặt:

```yaml
side1:
  roi:
    x: 100
    y: 80
    w: 500
    h: 900
```

Chỉnh `x, y, w, h` theo vị trí gá tem thực tế.

### `configs/threshold.yaml`

```yaml
blur_min: 80
brightness_min: 50
brightness_max: 220
ocr_confidence_min: 0.75
```

---

## Benchmark latency

Đo thời gian xử lý thực tế (mục tiêu < 1 giây / mặt):

```bash
# Dùng mock image (không cần ảnh thật)
python scripts/benchmark_latency.py --mock --runs 10

# Dùng ảnh thật
python scripts/benchmark_latency.py --side1 path/cam1.png path/cam2.png --runs 20

# Chỉ định template
python scripts/benchmark_latency.py --mock --template-id MY_TEMPLATE_ID --runs 10
```

Output:

```
  run   1/10    312.4 ms
  run   2/10    298.1 ms
  ...
--- Benchmark Results ---
  min    : 291.0 ms
  max    : 318.5 ms
  mean   : 304.2 ms
  median : 302.8 ms

  Target (<1000 ms median): PASS ✓
```

---

## Chạy tests

```bash
pytest -q
```

---

## Cấu trúc thư mục

```
src/
  api/          FastAPI routes, schemas, DI container
  capture/      Camera adapter, snapshot service
  compare/      Field / block / layout compare engine
  decision/     Side decision, overall decision, operator action
  domain/       Models, enums, error taxonomy
  ocr/          OCR engine (PaddleOCR / Tesseract / Mock)
  pipeline/     Inspection pipeline, orchestrator
  preprocess/   ROI crop, quality gate
  template_service/  Template lifecycle
  ui/           Streamlit pages và components
  db/           SQLite schema, repositories
  iot/          IoT publisher, callback client

configs/        Tất cả config YAML
scripts/        Init DB, benchmark, dataset tools
data/           SQLite DB, template images, captures
docs/           Spec, architecture, API contract
```

---

## Quick Start (TL;DR)

```bash
# 1. Tạo và activate venv
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Chọn OCR engine (chọn 1 trong 3)

# Option A: EasyOCR + KerasOCR (cần GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install easyocr keras-ocr tensorflow
# Sửa configs/ocr.yaml: engine: ensemble, gpu: true

# Option B: PaddleOCR (không cần GPU)
pip install paddlepaddle paddleocr
# Sửa configs/ocr.yaml: engine: paddleocr, gpu: false

# Option C: Tesseract (cài Tesseract trước)
pip install pytesseract
# Sửa configs/ocr.yaml: engine: tesseract, gpu: false

# 4. Khởi tạo database
python scripts/init_sqlite.py

# 5. Kiểm tra setup
python check_gpu_real.py  # Nếu dùng GPU
python docs/check_ocr_setup.py

# 6. Chạy server
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000

# 7. Mở trình duyệt
# http://127.0.0.1:8000
```

---

## Ghi chú

- Route `/inspection/side1` và `/side2` nhận file upload (dùng để test / debug)
- Route `/inspection/side1/live` và `/side2/live` chụp trực tiếp từ camera (dùng trên line thật)
- Template chưa `APPROVED` sẽ bị từ chối khi gọi runtime
- IoT mặc định ở chế độ `mock` — ghi file JSON vào `storage/iot_events/`

---

## Tài liệu tham khảo

- **GPU Setup**: `docs/GPU_SETUP.md`
- **Ensemble OCR Migration**: `docs/ENSEMBLE_OCR_MIGRATION.md`
- **Fix PyTorch CUDA**: `FIX_PYTORCH_STEPS.md`
- **Install PyTorch CUDA**: `INSTALL_PYTORCH_CUDA.md`
- **API Documentation**: http://127.0.0.1:8000/docs (sau khi start server)

---

## Liên hệ & Hỗ trợ

Nếu gặp vấn đề không có trong phần "Xử lý lỗi thường gặp", vui lòng:
1. Kiểm tra logs trong terminal
2. Chạy các script kiểm tra: `check_gpu_real.py`, `docs/check_ocr_setup.py`
3. Đọc tài liệu trong thư mục `docs/`
4. Mở issue trên repository
