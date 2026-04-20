# Garment Label Inspection

Hệ thống AI kiểm tra tem quần áo 2 mặt theo luồng:

```
Upload template → OCR full → Review / Approve
→ Side1 capture → Compare → Confirm
→ Side2 capture → Compare → Overall → IoT
```

---

## Yêu cầu

- Python 3.9+
- (Tuỳ chọn) PaddleOCR hoặc Tesseract để OCR thật
- (Tuỳ chọn) OpenCV nếu dùng camera thật

---

## Cài đặt

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Nếu chỉ muốn chạy local không cần OCR thật, bỏ qua `paddleocr` và `opencv-python` cũng được — hệ thống sẽ tự fallback về mock.

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

## Chạy Web UI + API server

Web UI được tích hợp trực tiếp vào API server (Jinja2 + HTML/CSS/JS thuần).

```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Mở trình duyệt tại [http://127.0.0.1:8000](http://127.0.0.1:8000)

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

API JSON vẫn có tại `/api/...` — xem Swagger tại [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Cần cài thêm `jinja2` nếu chưa có:

```bash
pip install jinja2
```

---

## Chạy UI (Streamlit)

```bash
streamlit run src/ui/dashboard_app.py
```

Mở trình duyệt tại [http://localhost:8501](http://localhost:8501)

Các trang:

| Trang | Mục đích |
|---|---|
| 01 Live Monitor | Runtime inspection side1 / side2 |
| 02 History | Tra cứu lịch sử kiểm tra |
| 03 Templates | Upload, review, approve template |
| 04 Bad Cases | Xem lại các case NG / UNCERTAIN |
| 05 Statistics | Thống kê tổng hợp KPI |

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

## Ghi chú

- Route `/inspection/side1` và `/side2` nhận file upload (dùng để test / debug)
- Route `/inspection/side1/live` và `/side2/live` chụp trực tiếp từ camera (dùng trên line thật)
- Template chưa `APPROVED` sẽ bị từ chối khi gọi runtime
- IoT mặc định ở chế độ `mock` — ghi file JSON vào `storage/iot_events/`










Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass 

.venv\Scripts\activate


python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000