````md id="k3f9q2"
# ĐẶC TẢ DEV + THIẾT KẾ GIAO DIỆN
## Dự án: Hệ thống AI kiểm tra tem quần áo 2 mặt

---

# 1. MỤC TIÊU DỰ ÁN

Xây dựng hệ thống kiểm tra tem quần áo 2 mặt với các yêu cầu sau:

- Tem được đặt **cố định** theo gá
- Camera được đặt **cố định**
- Có **2 camera**
- Kiểm tra theo thứ tự:
  - kiểm tra `side1`
  - người dùng bấm nút xác nhận
  - kiểm tra `side2`
- Khi upload template:
  - OCR toàn bộ dữ liệu của template
  - lưu lại toàn bộ dữ liệu chuẩn
  - dựng preview cho người dùng kiểm tra
  - chỉ template đã duyệt mới được dùng
- Khi runtime:
  - OCR toàn bộ dữ liệu của từng mặt
  - so sánh với template đã duyệt
  - báo lỗi riêng từng mặt
  - tổng hợp kết quả cuối
- Mục tiêu xử lý:
  - `< 1 giây / mặt`
  - không tính thời gian chờ người dùng bấm nút chuyển mặt 2

---

# 2. PHẠM VI HỆ THỐNG

## In scope
- 1 line
- 2 camera cố định
- 1 vị trí gá tem cố định
- kiểm tra 2 mặt của cùng 1 tem
- side1 kiểm trước, side2 kiểm sau
- có bước xác nhận thủ công giữa 2 mặt
- template upload + review + approve
- OCR full template
- OCR full runtime theo từng mặt
- publish kết quả sang IoT
- lưu ảnh bằng chứng
- hiển thị UI review + UI runtime

## Out of scope
- tem đặt tự do không cố định
- auto orientation phức tạp
- nhiều line cùng lúc
- auto template selection hoàn toàn
- self-learning
- production scale lớn ngay từ đầu
- multi-camera fusion phức tạp ngoài 2 camera hiện tại

---

# 3. NGUYÊN TẮC THIẾT KẾ

## Không làm
- không so ảnh với ảnh
- không OCR vài zone nhỏ rồi bỏ phần còn lại
- không để AI tự approve template
- không runtime parse lại template từ đầu
- không ép mọi case thành OK/NG

## Bắt buộc làm
- template chuẩn có cấu trúc
- OCR full khi upload template
- lưu toàn bộ raw text + block + field
- runtime OCR full theo mặt
- normalize text trước khi compare
- compare theo block/field
- severity theo `critical | major | minor`
- giữ trạng thái `UNCERTAIN`

---

# 4. LUỒNG HỆ THỐNG TỔNG QUÁT

```text
Template Upload
-> Full OCR Template
-> Template Structuring
-> User Review / Approve
-> Ground Truth Store

Runtime side1
-> Trigger line
-> Capture cam1 + cam2
-> ROI Crop
-> OCR full side1
-> Normalize Text
-> Compare với template side1
-> side1_result
-> Hiển thị UI
-> Chờ user bấm "Xác nhận chuyển mặt 2"

Runtime side2
-> Capture cam1 + cam2
-> ROI Crop
-> OCR full side2
-> Normalize Text
-> Compare với template side2
-> side2_result
-> Hiển thị UI

Overall
-> Overall Decision
-> Annotate Errors
-> Lưu DB / Storage
-> Publish sang IoT
````

---

# 5. KIẾN TRÚC MODULE

## 5.1. Template Upload Service

### Chức năng

* nhận file mẫu đúng
* hỗ trợ ảnh hoặc PDF
* tạo:

  * `template_id`
  * `template_version`
  * metadata template

### Input

* `template_name`
* `product_code`
* `side1_file`
* `side2_file`
* `created_by`

### Output

* record template ở trạng thái `DRAFT`

---

## 5.2. Full Template OCR Service

### Chức năng

* OCR toàn bộ nội dung của template upload
* xử lý riêng:

  * `side1`
  * `side2`
* trích:

  * raw text
  * text blocks
  * line order
  * bbox per block
  * confidence

### Output

```json
{
  "template_id": "LABEL_A01",
  "side1_raw_text": "....",
  "side1_blocks": [],
  "side2_raw_text": "....",
  "side2_blocks": []
}
```

---

## 5.3. Template Structuring Service

### Chức năng

* map full OCR text thành:

  * block
  * field
  * symbol area
  * order
* sinh template có cấu trúc

### Mỗi field phải có

* `field_name`
* `field_type: text | symbol | mixed`
* `required`
* `compare_type: exact | regex | fuzzy | symbol_match`
* `priority: critical | major | minor`
* `side`
* `expected_value`
* `bbox`

### Ví dụ schema

```json
{
  "template_id": "LABEL_A01",
  "template_version": "v1",
  "side1": {
    "raw_text": "....",
    "fields": [
      {
        "field_name": "product_code",
        "field_type": "text",
        "required": true,
        "compare_type": "exact",
        "priority": "critical",
        "expected_value": "C8-99/L31",
        "bbox": [100, 80, 220, 140]
      }
    ]
  },
  "side2": {
    "raw_text": "....",
    "fields": []
  }
}
```

---

## 5.4. Template Review Service

### Chức năng

* hiển thị:

  * ảnh gốc template
  * full OCR text
  * block OCR
  * field đã map
  * block chưa map
  * block confidence thấp
* cho user sửa:

  * field name
  * expected value
  * compare type
  * priority
  * bbox
* user approve template

### Trạng thái template

* `DRAFT`
* `REVIEW_REQUIRED`
* `APPROVED`
* `REJECTED`

### Rule

* template chưa `APPROVED` thì không được dùng cho runtime

---

## 5.5. Runtime Trigger Service

### Chức năng

* nhận trigger từ line/IoT
* tạo `scan_job_id`
* dừng line
* mở luồng kiểm `side1`
* sau `side1_done` thì chờ user confirm
* khi user bấm nút thì mở luồng kiểm `side2`

### Runtime states

* `WAIT_SIDE1_CAPTURE`
* `SIDE1_PROCESSING`
* `SIDE1_DONE_WAIT_CONFIRM`
* `WAIT_SIDE2_CAPTURE`
* `SIDE2_PROCESSING`
* `OVERALL_DONE`

---

## 5.6. Capture Service

### Chức năng

* chụp ảnh từ `cam1`, `cam2`
* áp dụng cho:

  * `side1`
  * `side2`
* lưu raw image

### Giả định bắt buộc

* tem đặt cố định theo gá
* camera cố định
* ROI gần cố định

### Output

* `side1_cam1_image`
* `side1_cam2_image`
* `side2_cam1_image`
* `side2_cam2_image`

---

## 5.7. ROI Crop / Quality Check Service

### Chức năng

* crop ROI cố định theo gá
* kiểm tra:

  * đủ tem hay chưa
  * blur
  * brightness
  * crop thiếu
  * print quality sơ bộ

### Nếu lỗi

* sinh:

  * `LOW_IMAGE_QUALITY`
  * hoặc `UNCERTAIN_RESULT`

---

## 5.8. Runtime Full OCR Service

### Chức năng

* OCR full toàn bộ nội dung của mặt đang kiểm
* chạy trên:

  * ROI từ cam1
  * ROI từ cam2
* xuất:

  * raw text
  * blocks
  * lines
  * confidence

### Ghi chú

Runtime vẫn OCR full, nhưng chỉ trên ROI cố định của tem, không OCR toàn frame.

---

## 5.9. Text Normalization Service

### Chức năng

Chuẩn hóa text OCR trước khi compare:

* trim whitespace
* collapse multiple spaces
* normalize line breaks
* normalize punctuation nếu field cho phép
* normalize ký tự OCR dễ nhầm
* chuẩn hóa hoa/thường nếu field cho phép

### Lưu ý

Không normalize quá mạnh với field critical như:

* `product_code`
* `size`
* `country_of_origin`
* `care_symbol chính`

---

## 5.10. Compare Engine

### Chức năng

So sánh runtime OCR với template đã approved theo 3 mức:

### A. Field-level compare

So từng field theo `compare_type`:

* `exact`
* `regex`
* `fuzzy`
* `symbol_match`

### B. Block-level compare

So block text dài:

* composition
* importer
* text pháp lý
* multilingual text

### C. Layout-level compare

So:

* thứ tự block
* vị trí tương đối
* block bị thiếu
* block bị thừa

### Error taxonomy

* `TEXT_MISMATCH`
* `MISSING_FIELD`
* `EXTRA_FIELD`
* `LAYOUT_MISMATCH`
* `SYMBOL_MISMATCH`
* `LOW_PRINT_QUALITY`
* `LOW_IMAGE_QUALITY`
* `WRONG_TEMPLATE`
* `UNCERTAIN_RESULT`

### Output mỗi error

```json
{
  "side": "side1",
  "camera_source": "cam1",
  "field": "size",
  "error_type": "TEXT_MISMATCH",
  "severity": "critical",
  "expected_value": "L",
  "actual_value": "M",
  "bbox": [120, 80, 220, 140],
  "confidence": 0.97
}
```

---

## 5.11. Side Decision Engine

### Chức năng

* tổng hợp kết quả từ `cam1` và `cam2` cho từng mặt
* ra:

  * `side1_result`
  * `side2_result`

### Rule

#### `OK`

* mọi field critical đúng
* field required đủ
* không có mismatch critical
* quality đạt

#### `NG`

* field critical sai
* field required thiếu
* symbol sai
* layout sai vượt ngưỡng

#### `UNCERTAIN`

* quality thấp
* OCR confidence thấp
* 2 camera mâu thuẫn
* block quan trọng không map được

---

## 5.12. Overall Decision Engine

### Chức năng

Tổng hợp:

* `side1_status`
* `side2_status`
  -> `overall_status`

### Rule

```text
Nếu side1 = OK và side2 = OK -> overall = OK
Nếu side1 = NG hoặc side2 = NG -> overall = NG
Nếu không có NG nhưng có ít nhất 1 mặt = UNCERTAIN -> overall = UNCERTAIN
```

---

## 5.13. Annotator Service

### Chức năng

* highlight bbox lỗi trên ảnh
* sinh evidence image theo từng mặt và từng camera

### Output

* `side1_cam1_annotated`
* `side1_cam2_annotated`
* `side2_cam1_annotated`
* `side2_cam2_annotated`

---

## 5.14. UI Service

### Chức năng

Hiển thị đầy đủ:

### Template review mode

* ảnh template side1 / side2
* full OCR text
* structured fields
* block chưa map
* chỗ confidence thấp
* nút approve/reject

### Runtime mode

* ảnh cam1/cam2 của side1
* side1 OCR text
* side1 diff với template
* side1 errors
* nút `Xác nhận chuyển mặt 2`
* ảnh cam1/cam2 của side2
* side2 OCR text
* side2 diff với template
* side2 errors
* overall result

---

## 5.15. IoT Publisher

### Chức năng

Publish action cuối sang IoT:

* `CONTINUE`
* `ALARM`
* `STOP_LINE`
* `RECHECK`

### Mapping gợi ý

* `overall = OK` -> `CONTINUE`
* `overall = NG` + critical -> `STOP_LINE`
* `overall = NG` + major -> `ALARM`
* `overall = UNCERTAIN` -> `RECHECK`

---

# 6. THIẾT KẾ GIAO DIỆN

## 6.1. Màn hình 1 — Dashboard tổng quan

### Mục đích

Cho vận hành xem nhanh tình trạng hệ thống.

### Thành phần

* Trạng thái line:

  * Running
  * Waiting
  * Inspecting Side1
  * Waiting Confirm Side2
  * Inspecting Side2
  * Stop
* Template đang dùng
* Số lượng đã kiểm
* Số lượng OK
* Số lượng NG
* Số lượng UNCERTAIN
* Tỷ lệ lỗi
* Nút:

  * Bắt đầu
  * Dừng
  * Reload
  * Xem lịch sử

### Layout gợi ý

* Header trên cùng
* 4 card KPI
* 1 panel trạng thái line
* 1 bảng lịch sử 10 bản ghi gần nhất

---

## 6.2. Màn hình 2 — Upload Template

### Mục đích

Upload file template chuẩn cho side1 và side2.

### Thành phần

* Input `Template Name`
* Input `Product Code`
* Upload file `Side1`
* Upload file `Side2`
* Button:

  * `Upload`
  * `Clear`
* Khu preview ảnh sau upload

### Kết quả sau upload

* sinh `template_id`
* chuyển template sang trạng thái `DRAFT`

---

## 6.3. Màn hình 3 — Review Template

### Mục đích

Người dùng xem và duyệt template sau khi OCR.

### Layout 2 cột

#### Cột trái

* Ảnh template side1
* Ảnh template side2

#### Cột phải

* OCR full text side1
* OCR full text side2
* danh sách field đã map
* block chưa map
* block confidence thấp

### Khu chỉnh sửa field

Mỗi field có:

* `field_name`
* `side`
* `expected_value`
* `compare_type`
* `priority`
* `required`
* `bbox`

### Button

* `Add Field`
* `Edit Field`
* `Delete Field`
* `Save Draft`
* `Approve Template`
* `Reject Template`

### Rule UI

* nếu còn block confidence thấp hoặc thiếu field required thì highlight màu vàng/đỏ
* template chưa approve thì không hiện trong danh sách chọn runtime

---

## 6.4. Màn hình 4 — Runtime Inspection

### Mục đích

Dùng khi kiểm tra thật trên line.

### Khu A — Side1

* Ảnh cam1 side1
* Ảnh cam2 side1
* OCR text side1
* diff expected/actual
* danh sách lỗi side1
* trạng thái side1:

  * OK
  * NG
  * UNCERTAIN

### Khu B — Button chuyển mặt

* Button lớn:

  * `Xác nhận chuyển mặt 2`

### Khu C — Side2

* Ảnh cam1 side2
* Ảnh cam2 side2
* OCR text side2
* diff expected/actual
* danh sách lỗi side2
* trạng thái side2

### Khu D — Overall

* `overall_status`
* `operator_action_required`
* severity cao nhất
* thời gian xử lý side1
* thời gian xử lý side2

### Khu E — Action

* `Continue`
* `Alarm`
* `Stop Line`
* `Recheck`

---

## 6.5. Màn hình 5 — Lịch sử kiểm tra

### Mục đích

Tra cứu lại các lần kiểm.

### Bảng dữ liệu

* `scan_job_id`
* `template_id`
* `time`
* `side1_status`
* `side2_status`
* `overall_status`
* `action`
* `operator`
* `line_id`

### Bộ lọc

* theo thời gian
* theo template
* theo trạng thái
* theo mã hàng

### Chi tiết từng record

Khi click vào 1 record:

* hiển thị 4 ảnh:

  * side1 cam1
  * side1 cam2
  * side2 cam1
  * side2 cam2
* ảnh khoanh lỗi
* OCR text
* lỗi chi tiết

---

## 6.6. Màn hình 6 — Cài đặt Rule

### Mục đích

Quản lý compare rule và severity.

### Thành phần

* danh sách field
* compare type
* priority
* required
* threshold fuzzy
* threshold confidence

### Button

* `Save`
* `Reset`
* `Clone Rule Set`

---

# 7. DATABASE / STORAGE SCHEMA TỐI THIỂU

## Tables

* `templates`
* `template_versions`
* `template_sides`
* `template_fields`
* `template_blocks`
* `scan_jobs`
* `captures`
* `ocr_results`
* `compare_results`
* `side_results`
* `overall_results`
* `iot_publish_logs`

## Object storage

* template original images
* side1/side2 raw captures
* annotated evidence images

---

# 8. API CONTRACT

## 8.1. Upload template

```json
{
  "template_name": "LABEL_A01",
  "product_code": "P001",
  "template_file_side1": "binary_or_path",
  "template_file_side2": "binary_or_path",
  "created_by": "user_id"
}
```

## 8.2. Runtime side1

```json
{
  "scan_job_id": "LINE01_ST01_000001",
  "template_id": "LABEL_A01",
  "current_stage": "SIDE1_INSPECTION",
  "side1_cam1_image": "binary_or_path",
  "side1_cam2_image": "binary_or_path"
}
```

## 8.3. Confirm side2

```json
{
  "scan_job_id": "LINE01_ST01_000001",
  "action": "CONFIRM_SIDE2"
}
```

## 8.4. Runtime side2

```json
{
  "scan_job_id": "LINE01_ST01_000001",
  "template_id": "LABEL_A01",
  "current_stage": "SIDE2_INSPECTION",
  "user_confirmed_side2": true,
  "side2_cam1_image": "binary_or_path",
  "side2_cam2_image": "binary_or_path"
}
```

## 8.5. Output result

```json
{
  "scan_job_id": "LINE01_ST01_000001",
  "template_id": "LABEL_A01",

  "side1_result": {
    "status": "NG",
    "raw_text": "....",
    "errors": [
      {
        "field": "size",
        "error_type": "TEXT_MISMATCH",
        "severity": "critical",
        "expected_value": "L",
        "actual_value": "M",
        "bbox": [120, 80, 220, 140]
      }
    ],
    "annotated_images": {
      "cam1": "path_or_url",
      "cam2": "path_or_url"
    }
  },

  "side2_result": {
    "status": "OK",
    "raw_text": "....",
    "errors": [],
    "annotated_images": {
      "cam1": "path_or_url",
      "cam2": "path_or_url"
    }
  },

  "overall_status": "NG",
  "operator_action_required": "STOP_LINE",
  "processing_time_ms_side1": 620,
  "processing_time_ms_side2": 590,
  "publish_to_iot": true
}
```

---

# 9. DATASET REQUIREMENT

## 9.1. Template dataset

Mỗi template cần:

* ảnh/PDF đúng của side1
* ảnh/PDF đúng của side2
* full OCR text
* field definitions
* expected values
* compare rules
* priority

## 9.2. Runtime dataset

Mỗi sample cần:

* `side1_cam1`
* `side1_cam2`
* `side2_cam1`
* `side2_cam2`

## 9.3. Test cases tối thiểu

* side1 đúng, side2 đúng
* side1 sai text, side2 đúng
* side1 đúng, side2 sai text
* side1 sai layout, side2 đúng
* side1 đúng, side2 sai layout
* side1 low quality, side2 ok
* side1 ok, side2 low quality
* cam1 và cam2 cùng đúng
* cam1 và cam2 mâu thuẫn
* symbol sai
* field critical sai
* field minor sai

---

# 10. RULE ƯU TIÊN FIELD

## Critical

* `product_code`
* `size`
* `care_symbol chính`
* `country_of_origin` nếu bắt buộc

## Major

* `material/composition`
* block text chính
* vị trí khối quan trọng

## Minor

* khoảng trắng
* format nhẹ
* sai ký tự không ảnh hưởng nghiệp vụ

---

# 11. CÁCH ĐẠT MỤC TIÊU DƯỚI 1 GIÂY

### Bắt buộc

* tem cố định
* camera cố định
* ROI cố định
* cache template metadata trong memory
* runtime chỉ OCR ROI tem
* normalize text gọn
* compare bằng text/block/field
* annotate làm sau decision

### Hiểu đúng

`< 1 giây` chỉ áp dụng cho:

* runtime side1
* runtime side2

Không áp dụng cho:

* upload template
* OCR full template
* review template
* thời gian chờ bấm nút chuyển mặt 2

---

# 12. OPEN QUESTIONS CẦN CHỐT

1. Runtime có bắt buộc so mọi dấu chấm/dấu phẩy không?
2. Cam1 và cam2 mâu thuẫn thì rule ưu tiên là gì?
3. Nếu side1 đã `NG critical` thì có còn cần kiểm side2 không?
4. OCR runtime dùng một engine hay nhiều engine voting?
5. Người dùng sửa template review ở mức block hay field?
6. Có cho phép block text dài chỉ kiểm fuzzy thay vì exact không?
7. Có cần lưu full raw OCR text của runtime vào DB không?
8. UI cuối cùng dùng Streamlit hay web app riêng?

---

# 13. KẾT LUẬN

Bản chốt cho dev là:

* **upload template = OCR full + structuring + review + approve**
* **runtime = OCR full trên ROI tem của từng mặt + compare với template chuẩn**
* **side1 kiểm trước**
* **user bấm xác nhận**
* **side2 kiểm sau**
* **mỗi mặt có lỗi riêng**
* **cuối cùng mới có overall result**
* **IoT nhận action cuối**
* **UI phải có 3 phần rõ ràng: upload/review template, runtime inspection, history**

Đây là bản đủ để:

* giao cho AI viết code theo module
* giao cho dev backend làm API
* giao cho dev UI dựng giao diện
* giao tiếp với team IoT

```
```




Viết code theo dạng SOLID và clean code để bảo trì và cải tiến 









Dưới đây là **plan chi tiết mới khi có web**. Mục tiêu không đổi: hệ thống vẫn phải chạy đúng luồng **upload template → OCR full + review/approve → runtime side1 → user confirm → runtime side2 → overall result → publish/mock IoT**, với **2 camera cho từng mặt**, input runtime là **4 ảnh** và output phải có `side1_result`, `side2_result`, `overall_status`, `operator_action_required`.  

---

# 1) Mục tiêu của giai đoạn có web

## Mục tiêu chính

Làm một **web nội bộ** để:

* review và approve template
* test runtime bằng ảnh upload tay hoặc ảnh chụp
* chạy đúng luồng `side1 -> confirm -> side2 -> overall`
* hiển thị đầy đủ ảnh, OCR text, lỗi, expected/actual, ảnh evidence
* sinh `operator_action_required` theo rule, trước mắt có thể **mock IoT** thay vì nối thiết bị thật 

## Mục tiêu không đổi

* vẫn chỉ là **POC cho 1 line**
* **2 camera cố định**
* **1 vị trí gá tem cố định**
* **side1 trước, side2 sau**
* có bước **user confirm**
* chưa làm multi-line, auto template selection, self-learning, production scale lớn 

## Mục tiêu hiệu năng

Mục tiêu vẫn là **< 1 giây / mặt sau khi nhận đủ ảnh hợp lệ**, nhưng con số này chỉ áp cho runtime side1/side2, **không áp cho upload template, OCR template, review template, hoặc thời gian chờ user bấm confirm**. 

---

# 2) Nguyên tắc kiến trúc khi thêm web

## Không đổi lõi AI

Không được đập lại lõi hiện tại. Lõi xử lý vẫn là:

* `template_service`
* `pipeline`
* `ocr`
* `preprocess`
* `compare`
* `decision`
* `annotator`
* `db`
* `iot` 

## Web chỉ là lớp phía trên

Web chỉ làm 3 việc:

* nhận thao tác của người dùng
* gọi service ứng dụng
* hiển thị kết quả

Web **không gọi trực tiếp** từng hàm OCR/compare/decision. Web phải đi theo chuỗi: **page/API → app service → template_service/pipeline → db/iot → trả result về UI**. Cách này mới bám đúng kiến trúc đã chốt gồm `UI Service` tách riêng khỏi `Compare Engine`, `Decision Engine`, `IoT Publisher`. 

## Nguyên tắc xử lý ảnh

Runtime vẫn phải:

* OCR full theo **ROI của từng mặt**
* normalize text trước khi compare
* compare theo **field/block**
* giữ trạng thái `UNCERTAIN`
* không so ảnh với ảnh
* không OCR vài vùng nhỏ rồi bỏ phần còn lại
* không parse lại template từ đầu ở runtime 

---

# 3) Cấu trúc thư mục sau khi có web

Giữ nguyên các thư mục lõi hiện tại. Chỉ thêm hoặc hoàn thiện 3 nhóm:

## A. `src/api/`

Dùng cho FastAPI:

* `main.py`
* `deps.py`
* `schemas.py`
* `serializers.py`
* `routes/health.py`
* `routes/templates.py`
* `routes/inspection.py`
* `routes/results.py`
* `routes/iot.py`
* `routes/pages.py`

## B. `src/ui/`

Dùng cho giao diện web:

* `templates/base.html`
* `templates/home.html`
* `templates/template_review.html`
* `templates/side1.html`
* `templates/confirm_side2.html`
* `templates/side2.html`
* `templates/result.html`
* `templates/history.html`
* `static/css/app.css`
* `static/js/*.js`

## C. `src/services/`

Lớp trung gian cho web:

* `template_app_service.py`
* `inspection_app_service.py`
* `result_app_service.py`
* `iot_app_service.py`

Lõi AI vẫn đi qua:

* `src/template_service/`
* `src/pipeline/`
* `src/ocr/`
* `src/preprocess/`
* `src/compare/`
* `src/decision/`
* `src/annotator/`
* `src/db/`
* `src/iot/` 

---

# 4) Luồng nghiệp vụ đầy đủ khi có web

## Luồng 1: Template

1. User mở màn hình review template
2. Upload `template_file_side1`, `template_file_side2`
3. Hệ thống OCR full 2 mặt
4. Hệ thống structure thành field/block
5. Web hiển thị:

   * ảnh template
   * full OCR text
   * field đã map
   * block chưa map
   * confidence thấp
6. User sửa field nếu cần
7. User bấm approve
8. Template chuyển sang `APPROVED`
9. Rule bắt buộc: template chưa `APPROVED` thì không được dùng cho runtime 

## Luồng 2: Runtime side1

1. User chọn template đã approved
2. Hệ thống nhận `side1_cam1_image`, `side1_cam2_image`
3. Runtime pipeline chạy:

   * crop ROI
   * quality gate
   * OCR full ROI
   * normalize
   * compare
   * side decision
   * annotate
4. Trả `side1_result`
5. State chuyển sang `SIDE1_DONE_WAIT_CONFIRM` 

## Luồng 3: Confirm side2

1. Web hiển thị kết quả side1
2. User bấm `Xác nhận chuyển mặt 2`
3. State chuyển sang `WAIT_SIDE2_CAPTURE` 

## Luồng 4: Runtime side2

1. User upload `side2_cam1_image`, `side2_cam2_image`
2. Pipeline chạy tương tự side1
3. Trả `side2_result`
4. Hệ thống tính `overall_status`
5. Hệ thống tính `operator_action_required`
6. Lưu DB, ảnh, log
7. Nếu chưa có IoT thật thì ghi mock action log thay cho publish thật 

---

# 5) Các màn hình web phải có

## 1. Home

Chỉ là trang điều hướng:

* vào Template Review
* vào Run Side1
* vào History

## 2. Template Review

Bắt buộc phải có:

* upload side1 template
* upload side2 template
* xem full OCR text
* xem danh sách field
* sửa field name / expected value / compare type / priority / bbox
* approve / reject

## 3. Run Side1

Bắt buộc phải có:

* chọn template approved
* upload/chụp `side1_cam1_image`
* upload/chụp `side1_cam2_image`
* nút chạy
* xem side1 OCR text
* xem lỗi side1
* xem diff với template
* xem status side1

## 4. Confirm Side2

* hiển thị side1 result
* nút `Xác nhận chuyển mặt 2`

## 5. Run Side2

* upload/chụp `side2_cam1_image`
* upload/chụp `side2_cam2_image`
* chạy
* xem OCR text
* xem lỗi side2
* xem status side2

## 6. Result

* `side1_result`
* `side2_result`
* `overall_status`
* `operator_action_required`
* `annotated_images`
* `processing_time_ms_side1`
* `processing_time_ms_side2`

## 7. History

* danh sách scan jobs
* click xem chi tiết job cũ

Các màn hình này bám trực tiếp vào phần `UI Service` và `Output contract` đã chốt. 

---

# 6) API phải có khi thêm web

## Template APIs

* `POST /api/templates/upload`
* `GET /api/templates/{template_id}/preview`
* `PUT /api/templates/{template_id}/fields`
* `POST /api/templates/{template_id}/approve`
* `GET /api/templates/approved`

## Inspection APIs

* `POST /api/inspection/side1`
* `POST /api/inspection/{scan_job_id}/confirm-side2`
* `POST /api/inspection/side2`
* `GET /api/results/{scan_job_id}`
* `GET /api/results/recent`

## IoT APIs

* `GET /api/iot/logs`

Nếu sau này có IoT thật thì mới thêm:

* `POST /api/iot/trigger`
* `POST /api/iot/ack`
* `GET /api/iot/health` 

---

# 7) Mapping web vào code hiện tại

## `template_app_service.py`

Nhiệm vụ:

* gọi `template_service/service.py`
* upload template
* lấy preview
* update fields
* approve template

## `inspection_app_service.py`

Nhiệm vụ:

* gọi `pipeline/orchestrator.py`
* chạy side1
* confirm side2
* chạy side2
* trả overall result

## `result_app_service.py`

Nhiệm vụ:

* đọc `scan_result_repo.py`
* trả result detail
* trả recent results

## `iot_app_service.py`

Nhiệm vụ:

* gọi `iot/ack_service.py`
* log action mock
* đọc `iot_publish_logs`

Tức là web không gọi thẳng vào `ocr`, `compare`, `decision`. Web chỉ gọi **app service**, còn app service mới nối sang lõi AI. 

---

# 8) Plan triển khai theo giai đoạn

## Giai đoạn 0 — Chốt rule trước khi code

Phải chốt ít nhất 6 câu:

1. Field nào là `critical`, `major`, `minor`
2. Cam1 và cam2 mâu thuẫn thì ưu tiên thế nào
3. Nếu side1 đã `NG critical` thì có cần kiểm side2 nữa không
4. Normalize punctuation mạnh đến mức nào
5. Template review sửa ở mức field hay block
6. Có cần lưu full raw OCR text runtime vào DB không

Đây đều là các open question trong đặc tả; không chốt thì web làm xong vẫn sai nghiệp vụ. 

## Giai đoạn 1 — Dựng web shell

Làm:

* `src/api/main.py`
* page routes
* base layout
* home page
* static css/js

Đầu ra:

* web chạy được local
* mở được bằng browser nội bộ
* vào được các page trống

## Giai đoạn 2 — Template flow

Làm:

* upload template 2 mặt
* OCR full template
* preview
* chỉnh field
* approve

Đầu ra:

* có ít nhất 1 template `APPROVED`
* runtime chỉ nhìn thấy template approved

## Giai đoạn 3 — Side1 flow

Làm:

* form upload `side1_cam1_image`, `side1_cam2_image`
* gọi inspection pipeline
* hiển thị side1 errors
* hiển thị state `SIDE1_DONE_WAIT_CONFIRM`

Đầu ra:

* side1 chạy end-to-end được

## Giai đoạn 4 — Confirm + Side2 flow

Làm:

* nút confirm side2
* form upload side2
* chạy pipeline side2
* tính overall

Đầu ra:

* luồng `side1 -> confirm -> side2 -> overall` chạy được end-to-end

## Giai đoạn 5 — Result + mock IoT

Làm:

* result page
* action mapping `CONTINUE/ALARM/STOP_LINE/RECHECK`
* lưu mock log vào `iot_publish_logs`

Đầu ra:

* web hiển thị kết quả cuối và action cuối

## Giai đoạn 6 — History + audit

Làm:

* history page
* result detail page
* đọc lại ảnh, lỗi, OCR, expected/actual
* truy vết scan job

Đầu ra:

* debug được job cũ

## Giai đoạn 7 — Hoàn thiện AI evidence

Làm:

* ảnh annotate thật
* không chỉ lưu summary JSON
* hiển thị bbox lỗi đúng cho cam1/cam2 từng mặt

Đầu ra:

* result page có bằng chứng trực quan

## Giai đoạn 8 — Test data + benchmark

Làm:

* dataset template chuẩn
* dataset runtime chuẩn theo 4 ảnh
* test case tối thiểu:

  * side1 đúng side2 đúng
  * side1 sai text
  * side2 sai text
  * side1/side2 low quality
  * cam1 và cam2 mâu thuẫn
  * field critical sai
  * field minor sai

Đầu ra:

* checklist test
* benchmark runtime per side 

---

# 9) Dữ liệu và DB cần đủ cho web

## Input template

* `template_name`
* `product_code`
* `template_file_side1`
* `template_file_side2`
* `created_by`

## Input runtime side1

* `scan_job_id`
* `template_id`
* `current_stage`
* `side1_cam1_image`
* `side1_cam2_image`

## Input runtime side2

* `scan_job_id`
* `template_id`
* `current_stage`
* `user_confirmed_side2`
* `side2_cam1_image`
* `side2_cam2_image`

## Output bắt buộc

* `side1_result`
* `side2_result`
* `overall_status`
* `operator_action_required`
* `annotated_images`
* `processing_time_ms_side1`
* `processing_time_ms_side2`
* `publish_to_iot`

## DB tối thiểu

* `templates`
* `template_versions`
* `template_sides`
* `template_fields`
* `template_blocks`
* `scan_jobs`
* `captures`
* `ocr_results`
* `compare_results`
* `side_results`
* `overall_results`
* `iot_publish_logs` 

---

# 10) Cái gì chưa làm ngay

Chưa làm ngay:

* IoT thật
* trigger line thật
* multi-line
* auto template selection
* self-learning
* production scale lớn
* multi-camera fusion phức tạp ngoài 2 camera hiện tại 

---

# 11) Plan ngắn gọn để bạn bám làm

## Sprint 1

* dựng `main.py`
* dựng page routes
* làm home + base layout
* làm template upload page

## Sprint 2

* làm template preview
* làm update fields
* làm approve template

## Sprint 3

* làm page side1
* nối `inspection_app_service.run_side1()`
* hiển thị side1 result

## Sprint 4

* làm confirm page
* làm page side2
* nối `run_side2()`
* hiển thị overall result

## Sprint 5

* mock IoT action
* history page
* detail result page

## Sprint 6

* evidence image thật
* test data
* benchmark
* sửa open questions còn lại

---

# 12) Kết luận

Bản plan đúng khi có web là:

* **không đổi lõi AI**
* **thêm web ở trên**
* **thêm app service ở giữa**
* **chạy đúng luồng 2 mặt, 2 camera**
* **side1 trước, confirm, side2 sau**
* **web hiển thị kết quả**
* **IoT trước mắt mock**
* **sau đó mới nối thiết bị thật** 

