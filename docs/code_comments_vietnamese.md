# Hướng dẫn chi tiết code - Tiếng Việt

## Mục lục
1. [Capture Module](#capture-module)
2. [OCR Module](#ocr-module)
3. [Preprocess Module](#preprocess-module)
4. [Compare Module](#compare-module)
5. [Decision Module](#decision-module)
6. [Pipeline Module](#pipeline-module)
7. [API Routes](#api-routes)
8. [Services](#services)
9. [Database](#database)
10. [Utils](#utils)

---

## Capture Module

### `src/capture/camera_adapter.py`

**Mục đích**: Adapter pattern cho việc chụp ảnh từ camera — hỗ trợ nhiều backend (OpenCV thật, Mock test).

#### `CameraFrame`
```python
@dataclass(frozen=True)
class CameraFrame:
    camera_id: str      # ID camera (cam1, cam2)
    content: bytes      # Ảnh dạng bytes (PNG)
    media_type: str     # MIME type (image/png)
    width: int          # Chiều rộng ảnh
    height: int         # Chiều cao ảnh
```

#### `BaseCameraAdapter` (Abstract)
Interface chung cho tất cả camera adapter.

**Method `capture(camera_id: str) -> CameraFrame`**
- Chụp 1 frame từ camera
- Trả về CameraFrame chứa ảnh bytes

**Method `to_capture_input(camera_id: str) -> CaptureInput`**
- Wrapper chuyển CameraFrame → CaptureInput (domain model)
- Tự động đặt tên file: `{camera_id}_frame.png`

#### `OpenCVCameraAdapter`
Chụp ảnh thật từ camera USB/webcam qua OpenCV.

**Khởi tạo**:
- Check opencv-python đã cài chưa
- Load config từ `configs/camera.yaml`
- Config mặc định: cam1=index 0, cam2=index 1

**Method `capture()`**:
1. Mở camera theo index từ config
2. Set resolution (width, height)
3. Đọc 1 frame
4. Encode thành PNG bytes
5. Release camera
6. Trả về CameraFrame

**Lỗi có thể xảy ra**:
- RuntimeError: opencv-python chưa cài
- RuntimeError: Camera không capture được (bị chiếm, không tồn tại)

#### `MockCameraAdapter`
Trả về ảnh PNG 1×1 trắng — dùng cho test không cần camera thật.

**Use case**:
- Unit test
- Dev local không có camera
- CI/CD pipeline

#### `build_camera_adapter(strict: bool = False)`
Factory function tự động chọn adapter phù hợp.

**Logic**:
1. Nếu có opencv-python → dùng OpenCVCameraAdapter
2. Nếu không có và strict=False → fallback MockCameraAdapter
3. Nếu không có và strict=True → raise RuntimeError

**Khi nào dùng strict=True**:
- Production mode
- Muốn đảm bảo chắc chắn dùng camera thật
- Không cho phép chạy với mock

---

### `src/capture/snapshot.py`

**Mục đích**: Service chụp cả 2 camera cùng lúc cho 1 mặt tem.

#### `SideSnapshot`
```python
@dataclass(frozen=True)
class SideSnapshot:
    side: InspectionSide    # SIDE1 hoặc SIDE2
    cam1: CaptureInput      # Ảnh từ camera 1
    cam2: CaptureInput      # Ảnh từ camera 2
```

**Method `as_list() -> list[CaptureInput]`**
- Chuyển thành list [cam1, cam2] để truyền vào pipeline

#### `SnapshotService`
Service chụp ảnh runtime.

**Method `capture_side(side: InspectionSide) -> SideSnapshot`**
1. Gọi adapter.to_capture_input("cam1")
2. Gọi adapter.to_capture_input("cam2")
3. Wrap thành SideSnapshot
4. Trả về

**Lưu ý**:
- Service này reuse cùng 1 adapter instance
- Adapter được inject qua constructor (DI pattern)
- Mặc định dùng `build_camera_adapter()` nếu không inject

---

## OCR Module

### `src/ocr/engine.py`

**Mục đích**: OCR engine với nhiều backend (PaddleOCR, Tesseract, Mock) và auto-selection.

#### `OCRDocument`
```python
@dataclass(frozen=True)
class OCRDocument:
    side: InspectionSide        # Mặt nào (side1/side2)
    raw_text: str               # Full text OCR được
    blocks: list[OCRBlock]      # Danh sách text block với bbox
    engine_name: str            # Engine đã dùng (paddleocr/tesseract/mock)
```

#### `BaseOCREngine` (Abstract)
Interface chung cho tất cả OCR engine.

**Method `run(side, file) -> OCRDocument`**
- Input: InspectionSide + TemplateUploadFile
- Output: OCRDocument với text và blocks

#### `MockOCREngine`
OCR giả — decode text từ file hoặc trả về placeholder.

**Logic**:
- Nếu file là text → decode UTF-8
- Nếu file là binary → trả về "BINARY_FILE:{filename}"
- Nếu file rỗng → trả về "EMPTY_FILE:{filename}"

**Use case**:
- Unit test
- Dev không cần OCR thật
- Fallback khi không có backend

#### `PaddleOCREngine`
OCR thật dùng PaddleOCR (AI model mạnh, hỗ trợ nhiều ngôn ngữ).

**Khởi tạo**:
- Check paddleocr đã cài chưa
- Tạo PaddleOCR instance với config:
  - lang: "en" (hoặc "vi", "ch"...)
  - use_angle_cls: True (tự động xoay ảnh)

**Method `run()`**:
1. Lưu file tạm ra disk (PaddleOCR cần file path)
2. Gọi ocr.ocr(path)
3. Parse kết quả thành list[OCRBlock]
4. Render blocks thành raw_text
5. Xóa file tạm
6. Trả về OCRDocument

**Lưu ý**:
- PaddleOCR cần GPU để nhanh (CPU cũng chạy được nhưng chậm)
- Model tải lần đầu ~100MB

#### `TesseractOCREngine`
OCR thật dùng Tesseract (open-source, nhẹ hơn Paddle).

**2 mode**:
1. **pytesseract** (Python wrapper): nếu có cài pytesseract
2. **CLI** (command line): nếu có tesseract binary

**Method `run()`**:
- Thử pytesseract trước
- Nếu không có → thử CLI
- Nếu cả 2 đều không có → raise RuntimeError

**Ưu điểm**:
- Nhẹ, không cần GPU
- Cài đặt đơn giản

**Nhược điểm**:
- Độ chính xác thấp hơn PaddleOCR
- Không tự động xoay ảnh

#### `AutoOCREngine`
Engine thông minh — tự chọn backend tốt nhất có sẵn.

**Khởi tạo**:
- Load config từ `configs/ocr.yaml`
- Đọc `engine` (auto/paddleocr/tesseract/mock)
- Đọc `strict_real_ocr` (True/False)

**Method `run()`**:
1. Resolve engine order theo config:
   - Nếu engine=auto → thử [paddleocr, tesseract, mock]
   - Nếu engine=paddleocr → thử [paddleocr, mock]
2. Loop qua từng engine:
   - Thử build và run
   - Nếu thành công → return ngay
   - Nếu fail → thử engine tiếp theo
3. Nếu strict_real_ocr=True và không có engine thật → raise RuntimeError
4. Nếu strict_real_ocr=False → fallback về mock

**Khi nào dùng strict_real_ocr=True**:
- Production mode
- Muốn đảm bảo OCR thật 100%
- Không cho phép chạy với mock

**Config ví dụ**:
```yaml
# configs/ocr.yaml
engine: auto
lang: en
strict_real_ocr: false  # dev mode
# strict_real_ocr: true  # prod mode
```

---

## Preprocess Module

### `src/preprocess/crop.py`

**Mục đích**: Crop ROI cố định từ ảnh full frame theo config camera.

#### `crop_fixed_roi(capture, side) -> CaptureInput`

**Logic**:
1. Load ROI config từ `configs/camera.yaml`
2. Nếu capture là text fixture → pass through (không crop)
3. Nếu capture không phải image → pass through
4. Nếu không có PIL → pass through
5. Crop ảnh theo ROI: `image.crop((x, y, x+w, y+h))`
6. Lưu thành PNG bytes
7. Trả về CaptureInput mới với suffix `_roi`

**Config ví dụ**:
```yaml
# configs/camera.yaml
side1:
  roi:
    x: 100    # Tọa độ góc trên trái
    y: 80
    w: 500    # Chiều rộng ROI
    h: 900    # Chiều cao ROI
```

**Lưu ý**:
- ROI phải được đo thực tế trên line
- Tem phải đặt cố định theo gá
- Camera phải cố định

---

### `src/preprocess/quality_gate.py`

**Mục đích**: Kiểm tra chất lượng ảnh trước khi OCR — phân biệt lỗi ảnh vs lỗi in.

#### `QualityGateResult`
```python
@dataclass(frozen=True)
class QualityGateResult:
    passed: bool                # True = ảnh OK, False = ảnh lỗi
    score: float                # Điểm chất lượng 0.0-1.0
    error_type: ErrorType       # LOW_IMAGE_QUALITY / LOW_PRINT_QUALITY / UNCERTAIN
    reason: str                 # Lý do chi tiết
```

#### `evaluate_capture_quality(capture) -> QualityGateResult`

**Các bước kiểm tra**:

1. **Empty check**:
   - Nếu content rỗng → FAIL (LOW_IMAGE_QUALITY)

2. **Text fixture bypass**:
   - Nếu media_type là text → PASS (dùng cho test)

3. **Dimension check**:
   - Nếu width < 20px hoặc height < 20px → FAIL (UNCERTAIN_RESULT)
   - ROI quá nhỏ không thể OCR tin cậy

4. **Brightness check** (camera/lighting issue):
   - Tính brightness = mean pixel value (0-255)
   - Nếu < 40 → FAIL (LOW_IMAGE_QUALITY) "Image too dark"
   - Nếu > 220 → FAIL (LOW_IMAGE_QUALITY) "Image overexposed"

5. **Blur check** (camera focus issue):
   - Tính blur_proxy = sqrt(variance of edge image)
   - Nếu < 8 → FAIL (LOW_IMAGE_QUALITY) "Image blurry"

6. **Print quality check** (ink faint issue):
   - Tính contrast = stddev of pixel values
   - Nếu contrast < 10 và blur_proxy < 20 → FAIL (LOW_PRINT_QUALITY)
   - Ảnh rõ nhưng chữ mờ → lỗi in, không phải lỗi camera

7. **Composite score**:
   - brightness_score = 1 - |brightness - 128| / 128
   - blur_score = blur_proxy / 32
   - final_score = (brightness_score + blur_score) / 2

**Phân biệt lỗi**:
- `LOW_IMAGE_QUALITY`: Lỗi camera/lighting → cần fix phần cứng
- `LOW_PRINT_QUALITY`: Lỗi in tem → cần check mực in
- `UNCERTAIN_RESULT`: Không xác định được → cần review thủ công

**Threshold config**:
```yaml
# configs/threshold.yaml
blur_min: 80
brightness_min: 50
brightness_max: 220
```

---

## Compare Module

### `src/compare/compare_text.py`

**Mục đích**: So sánh text OCR với expected value theo nhiều mode.

#### `compare_text_field(expected, actual, compare_type, field_name, priority)`

**4 compare modes**:

1. **EXACT**: So sánh chính xác từng ký tự
   - Normalize: trim whitespace, collapse spaces
   - Nếu khác → TEXT_MISMATCH

2. **REGEX**: Match theo regex pattern
   - expected_value chứa regex pattern
   - Dùng re.search() để match
   - Nếu không match → TEXT_MISMATCH

3. **FUZZY**: So sánh gần đúng (cho phép sai vài ký tự)
   - Dùng rapidfuzz.fuzz.ratio()
   - Threshold mặc định: 85%
   - Nếu < threshold → TEXT_MISMATCH

4. **SYMBOL_MATCH**: So sánh symbol giặt/bảo quản
   - Delegate sang compare_symbols module

**Output**: `ComparisonError` hoặc None

---

### `src/compare/compare_layout.py`

**Mục đích**: So sánh layout (vị trí, thứ tự block) giữa template và runtime.

#### `compare_layout(template_blocks, runtime_blocks)`

**Kiểm tra**:
1. **Block order**: Thứ tự block có đúng không
2. **Block position**: Vị trí tương đối có đúng không (dùng IoU)
3. **Missing blocks**: Block nào bị thiếu
4. **Extra blocks**: Block nào thừa ra

**Output**: List[ComparisonError] với error_type = LAYOUT_MISMATCH

---

## Decision Module

### `src/decision/rules.py`

**Mục đích**: Quyết định status cuối (OK/NG/UNCERTAIN) dựa trên errors.

#### `SideDecisionEngine`

**Method `decide(errors, quality_ok) -> InspectionStatus`**

**Logic**:
1. Nếu quality_ok = False → UNCERTAIN
2. Nếu có error critical → NG
3. Nếu có error major và field required → NG
4. Nếu chỉ có error minor → OK (với warning)
5. Nếu không có error → OK

#### `OverallDecisionEngine`

**Method `decide(side1_status, side2_status) -> InspectionStatus`**

**Logic**:
```
Nếu side1 = OK và side2 = OK → overall = OK
Nếu side1 = NG hoặc side2 = NG → overall = NG
Nếu có ít nhất 1 mặt UNCERTAIN → overall = UNCERTAIN
```

---

### `src/decision/actions.py`

**Mục đích**: Quyết định operator action dựa trên overall status và severity.

#### `OperatorActionDecider`

**Method `decide(overall_status, highest_severity) -> OperatorAction`**

**Mapping**:
```
OK → CONTINUE
NG + critical → STOP_LINE
NG + major → ALARM
NG + minor → ALARM
UNCERTAIN → RECHECK
```

**Giải thích action**:
- `CONTINUE`: Tem OK, line chạy tiếp
- `ALARM`: Tem lỗi nhưng không nghiêm trọng, báo động
- `STOP_LINE`: Tem lỗi nghiêm trọng, dừng line ngay
- `RECHECK`: Không chắc chắn, cần kiểm tra thủ công

---

## Pipeline Module

### `src/pipeline/inspection_pipeline.py`

**Mục đích**: Pipeline xử lý 1 mặt tem từ ảnh → kết quả.

#### `InspectionPipeline`

**Method `inspect_side(template, input, scan_job_id) -> SideInspectionResult`**

**Luồng xử lý**:
1. **Crop ROI**: Crop ảnh theo config camera
2. **Quality gate**: Kiểm tra chất lượng ảnh
3. **OCR**: OCR full text từ cả 2 camera
4. **Normalize**: Chuẩn hóa text (trim, collapse spaces)
5. **Compare**: So sánh với template theo từng field
6. **Aggregate**: Tổng hợp lỗi từ 2 camera
7. **Decision**: Ra quyết định OK/NG/UNCERTAIN
8. **Annotate**: Vẽ bbox lỗi lên ảnh
9. **Save evidence**: Lưu ảnh annotate
10. **Return**: SideInspectionResult

**Xử lý 2 camera**:
- OCR cả cam1 và cam2
- Compare riêng từng camera
- Nếu 2 camera mâu thuẫn → chọn camera có confidence cao hơn
- Nếu cả 2 đều thấp → UNCERTAIN

---

### `src/pipeline/orchestrator.py`

**Mục đích**: Orchestrator quản lý state machine của toàn bộ luồng inspection.

#### `InspectionOrchestrator`

**State machine**:
```
WAIT_SIDE1_CAPTURE
  ↓ start_scan_job()
SIDE1_PROCESSING
  ↓ inspect_side1()
SIDE1_DONE_WAIT_CONFIRM
  ↓ confirm_side2()
WAIT_SIDE2_CAPTURE
  ↓ inspect_side2()
SIDE2_PROCESSING
  ↓ inspect_side2()
OVERALL_DONE
```

**Methods**:

1. **`start_scan_job(scan_job_id, template_id)`**
   - Tạo ScanJob mới
   - Validate template đã approve
   - State = WAIT_SIDE1_CAPTURE

2. **`inspect_side1(scan_job_id, input)`**
   - Validate state = WAIT_SIDE1_CAPTURE
   - Gọi pipeline.inspect_side()
   - Lưu side1_result
   - State = SIDE1_DONE_WAIT_CONFIRM

3. **`confirm_side2(scan_job_id)`**
   - Validate state = SIDE1_DONE_WAIT_CONFIRM
   - Check policy (có cho phép side2 nếu side1 NG không)
   - State = WAIT_SIDE2_CAPTURE

4. **`inspect_side2(scan_job_id, input)`**
   - Validate state = WAIT_SIDE2_CAPTURE
   - Gọi pipeline.inspect_side()
   - Lưu side2_result
   - Tổng hợp overall decision
   - Publish IoT
   - State = OVERALL_DONE

5. **`get_result(scan_job_id)`**
   - Lấy OverallInspectionResult
   - Chỉ có sau khi OVERALL_DONE

---

## API Routes

### `src/api/routes/inspection.py`

**2 nhóm routes**:

#### Upload mode (test/debug):
- `POST /api/inspection/side1` — upload cam1_file + cam2_file
- `POST /api/inspection/side2` — upload cam1_file + cam2_file

#### Live mode (production):
- `POST /api/inspection/side1/live` — chụp từ camera thật
- `POST /api/inspection/side2/live` — chụp từ camera thật

#### Shared:
- `POST /api/inspection/{id}/confirm-side2` — xác nhận chuyển mặt 2
- `GET /api/inspection/{id}/result` — lấy kết quả

---

### `src/api/routes/templates.py`

- `POST /api/templates/upload` — upload template mới
- `GET /api/templates/{id}` — lấy template record
- `GET /api/templates/{id}/preview` — lấy preview để review
- `PUT /api/templates/{id}/fields` — update fields
- `POST /api/templates/{id}/approve` — approve template
- `POST /api/templates/{id}/reject` — reject template

---

### `src/api/routes/counter.py`

- `GET /api/counter/summary` — KPI tổng hợp (total, OK, NG, UNCERTAIN, error_rate)
- `GET /api/counter/recent?limit=10` — N job gần nhất

---

### `src/api/routes/results.py`

- `GET /api/results/{id}` — lấy overall result của 1 job
- `GET /api/results/?limit=10` — list recent jobs

---

### `src/api/routes/iot.py`

- `GET /api/iot/events/{id}` — lấy log IoT publish của 1 job

---

## Database

### `src/db/schema.sql`

**13 tables**:

1. **templates**: Template metadata
2. **template_versions**: Version history
3. **template_sides**: Side1/side2 data
4. **template_fields**: Field definitions
5. **template_blocks**: OCR blocks
6. **scan_jobs**: Runtime job tracking
7. **captures**: Ảnh đã chụp
8. **ocr_results**: Kết quả OCR
9. **compare_results**: Lỗi so sánh
10. **side_results**: Kết quả từng mặt
11. **overall_results**: Kết quả tổng hợp
12. **iot_publish_logs**: Log publish IoT

---

## Utils

### `src/utils/config_loader.py`

**Function `load_yaml_config(path, default=None)`**
- Load YAML config file
- Nếu file không tồn tại → return default
- Nếu parse lỗi → return default

### `src/utils/paths.py`

**Constants**:
- `PROJECT_ROOT`: Thư mục gốc project
- `TEMPLATE_STORAGE`: storage/templates/
- `CAPTURE_STORAGE`: storage/captures/
- `ANNOTATION_STORAGE`: storage/annotations/
- `IOT_STORAGE`: storage/iot_events/

**Function `ensure_storage_tree()`**
- Tạo tất cả thư mục storage nếu chưa có

---

## Scripts

### `scripts/benchmark_latency.py`

**Mục đích**: Đo latency thực tế của 1 mặt (mục tiêu < 1 giây).

**Usage**:
```bash
# Mock mode
python scripts/benchmark_latency.py --mock --runs 10

# Real images
python scripts/benchmark_latency.py --side1 cam1.png cam2.png --runs 20
```

**Output**:
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

## Tổng kết luồng hoàn chỉnh

### 1. Upload Template
```
User upload side1.png + side2.png
  ↓
POST /api/templates/upload
  ↓
TemplateService.create_draft()
  ↓
OCR full cả 2 mặt
  ↓
Lưu DB với status = DRAFT
  ↓
Return template_id
```

### 2. Review Template
```
GET /api/templates/{id}/preview
  ↓
Hiển thị OCR text, fields, unmapped blocks
  ↓
User chỉnh sửa fields
  ↓
PUT /api/templates/{id}/fields
  ↓
POST /api/templates/{id}/approve
  ↓
Status = APPROVED
```

### 3. Runtime Inspection
```
POST /api/inspection/side1/live
  ↓
SnapshotService.capture_side(SIDE1)
  ↓
InspectionPipeline.inspect_side()
  ├─ Crop ROI
  ├─ Quality gate
  ├─ OCR
  ├─ Compare
  ├─ Decision
  └─ Annotate
  ↓
Return side1_result
  ↓
POST /api/inspection/{id}/confirm-side2
  ↓
POST /api/inspection/side2/live
  ↓
InspectionPipeline.inspect_side()
  ↓
OverallDecisionEngine.decide()
  ↓
OperatorActionDecider.decide()
  ↓
IoTAckService.publish_result()
  ↓
Return overall_result
```

---

## Best Practices

### 1. Error Handling
- Luôn validate input trước khi xử lý
- Raise exception rõ ràng với message chi tiết
- Catch exception ở controller layer, không để leak ra user

### 2. State Machine
- Luôn validate state trước khi chuyển
- Không cho phép skip state
- Log mọi state transition

### 3. Testing
- Mock camera adapter cho unit test
- Mock OCR engine cho integration test
- Dùng fixture ảnh thật cho E2E test

### 4. Performance
- Cache template metadata trong memory
- Chỉ OCR ROI, không OCR full frame
- Parallel xử lý 2 camera nếu cần

### 5. Monitoring
- Log mọi lần inspect với latency
- Track error rate theo template
- Alert khi latency > 1s

---

Tài liệu này cung cấp overview chi tiết về toàn bộ codebase.
Mỗi module có vai trò rõ ràng và interface sạch sẽ.
