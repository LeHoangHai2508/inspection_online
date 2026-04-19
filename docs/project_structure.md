# Cấu trúc thư mục dự án Garment Label Inspection

## Tổng quan

Dự án này là hệ thống kiểm tra nhãn mác quần áo tự động sử dụng Computer Vision và OCR.

```
GARMENT_LABEL_INSPECTION/
│
├── configs/                    # Các file cấu hình YAML
│   ├── app.yaml               # Cấu hình ứng dụng chính
│   ├── camera.yaml            # Cấu hình camera (ROI, resolution)
│   ├── db.yaml                # Cấu hình database
│   ├── infer.yaml             # Cấu hình model inference
│   ├── iot.yaml               # Cấu hình IoT broker (MQTT/HTTP)
│   ├── logging.yaml           # Cấu hình logging
│   ├── ocr.yaml               # Cấu hình OCR engine
│   ├── taxonomy_errors.yaml   # Định nghĩa các loại lỗi
│   ├── taxonomy_symbols.yaml  # Định nghĩa các ký hiệu care label
│   ├── threshold.yaml         # Ngưỡng cho quality gate và comparison
│   └── templates/             # Template configs
│       ├── TPL_001.yaml
│       ├── TPL_002.yaml
│       └── TPL_003.yaml
│
├── data/                       # Dữ liệu và datasets
│   ├── curated/               # Dữ liệu đã được xử lý và labeled
│   │   ├── detection/         # Dataset cho object detection
│   │   ├── field_gt/          # Ground truth cho các fields
│   │   ├── ocr_text/          # Dataset cho OCR training
│   │   ├── segmentation/      # Dataset cho segmentation
│   │   ├── splits/            # Train/val/test splits
│   │   └── symbol_cls/        # Dataset cho symbol classification
│   │
│   ├── external/              # Dữ liệu từ nguồn bên ngoài
│   │   ├── kaggle_ocr_chars_raw/
│   │   ├── rf_carelabels4_raw/
│   │   ├── rf_care_labels_v2_raw/
│   │   ├── rf_care_lable_raw/
│   │   ├── rf_care_symbols_raw/
│   │   └── rf_clothing_tag_raw/
│   │
│   ├── internal/              # Dữ liệu nội bộ
│   │   ├── badcases/          # Các trường hợp lỗi để phân tích
│   │   │   ├── need_relabel/  # Cần label lại
│   │   │   ├── ng/            # Lỗi thật
│   │   │   └── uncertain/     # Không chắc chắn
│   │   │
│   │   ├── runtime_raw/       # Ảnh chụp từ production line
│   │   │   ├── cam1/
│   │   │   ├── cam2/
│   │   │   └── metadata/
│   │   │
│   │   ├── templates/         # Template images và configs
│   │   │   ├── template_index.csv
│   │   │   └── TPL_001/
│   │   │       ├── back/
│   │   │       │   ├── template.png
│   │   │       │   └── zones.json
│   │   │       ├── front/
│   │   │       │   ├── template.png
│   │   │       │   └── zones.json
│   │   │       ├── fields.json
│   │   │       ├── meta.json
│   │   │       └── rules.json
│   │   │
│   │   └── test_cases/        # Test cases cho các scenarios
│   │       ├── blur/
│   │       ├── correct/
│   │       ├── crop_missing/
│   │       ├── layout_mismatch/
│   │       ├── low_light/
│   │       ├── size_mismatch/
│   │       ├── symbol_mismatch/
│   │       ├── text_mismatch/
│   │       ├── uncertain/
│   │       └── wrong_template/
│   │
│   └── sqlite/                # SQLite database files
│       └── inspection.db
│
├── docs/                       # Documentation
│   ├── annotation_guideline.md    # Hướng dẫn annotation
│   ├── api_contract.md            # API contract specification
│   ├── architecture.md            # Kiến trúc hệ thống
│   ├── callback_contract.md       # IoT callback contract
│   ├── code_comments_vietnamese.md # Tổng hợp comments code
│   ├── data_dictionary.md         # Data dictionary
│   ├── plan.md                    # Kế hoạch phát triển
│   ├── project_structure.md       # File này - Cấu trúc thư mục
│   └── runbook.md                 # Hướng dẫn vận hành
│
├── outputs/                    # Outputs từ training và experiments
│   ├── models/                # Trained models
│   ├── logs/                  # Training logs
│   └── experiments/           # Experiment results
│
├── scripts/                    # Utility scripts
│   ├── benchmark_latency.py       # Benchmark tốc độ xử lý
│   ├── build_detection_dataset.py # Tạo dataset detection
│   ├── build_field_gt.py          # Tạo ground truth cho fields
│   ├── build_symbol_dataset.py    # Tạo dataset symbols
│   ├── check_tables.py            # Kiểm tra database tables
│   ├── init_sqlite.py             # Khởi tạo SQLite database
│   ├── make_dirs.py               # Tạo cấu trúc thư mục
│   ├── merge_symbol_datasets.py   # Merge datasets
│   ├── remap_symbols.py           # Remap symbol taxonomy
│   └── split_dataset.py           # Split train/val/test
│
├── src/                        # Source code chính
│   │
│   ├── api/                   # FastAPI application
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── deps.py            # Dependency injection
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── serializers.py     # Object serialization
│   │   ├── _compat.py         # Compatibility layer
│   │   └── routes/            # API routes
│   │       ├── health.py      # Health check endpoint
│   │       ├── templates.py   # Template management
│   │       ├── inspection.py  # Inspection endpoints
│   │       ├── results.py     # Results query
│   │       ├── iot.py         # IoT events query
│   │       ├── counter.py     # KPI và statistics
│   │       └── pages.py       # Web UI page routes
│   │
│   ├── ui/                    # Web UI (HTML/CSS/JS)
│   │   ├── templates/         # Jinja2 templates
│   │   │   ├── base.html      # Base template
│   │   │   ├── home.html      # Dashboard home
│   │   │   ├── template_review.html  # Template review page
│   │   │   ├── side1.html     # Side1 inspection page
│   │   │   ├── confirm_side2.html    # Confirm side2 page
│   │   │   ├── side2.html     # Side2 inspection page
│   │   │   ├── result.html    # Result detail page
│   │   │   └── history.html   # History page
│   │   │
│   │   └── static/            # Static assets
│   │       ├── css/
│   │       │   └── app.css    # Main stylesheet
│   │       ├── js/
│   │       │   ├── template_review.js
│   │       │   ├── side1.js
│   │       │   ├── side2.js
│   │       │   └── result.js
│   │       └── img/           # Images
│   │
│   ├── services/              # Application services (Web UI logic)
│   │   ├── template_app_service.py    # Template UI service
│   │   ├── inspection_app_service.py  # Inspection UI service
│   │   ├── result_app_service.py      # Result UI service
│   │   └── iot_app_service.py         # IoT UI service
│   │
│   ├── template_service/      # Template management
│   │   ├── service.py         # Template business logic
│   │   ├── repository.py      # Template data access
│   │   └── validators.py      # Template validation
│   │
│   ├── pipeline/              # Inspection pipeline
│   │   ├── inspection_pipeline.py     # Main pipeline
│   │   ├── orchestrator.py            # Business flow orchestrator
│   │   ├── single_view_pipeline.py    # Single camera pipeline
│   │   └── dual_view_pipeline.py      # Dual camera pipeline
│   │
│   ├── ocr/                   # OCR module
│   │   ├── engine.py          # OCR engine (PaddleOCR/Tesseract)
│   │   ├── parser.py          # Parse OCR output
│   │   ├── postprocess.py     # OCR postprocessing
│   │   └── run_ocr.py         # OCR runner
│   │
│   ├── preprocess/            # Image preprocessing
│   │   ├── crop.py            # Crop ROI
│   │   ├── normalize.py       # Normalize brightness/contrast
│   │   ├── quality_gate.py    # Quality checks
│   │   ├── detect_label.py    # Detect label region
│   │   ├── rectify.py         # Rectify perspective
│   │   └── segment_label.py   # Segment label
│   │
│   ├── compare/               # Comparison logic
│   │   ├── aggregate_verify.py        # Aggregate results
│   │   ├── compare_text.py            # Compare text fields
│   │   ├── compare_required_fields.py # Check required fields
│   │   ├── compare_layout.py          # Compare layout
│   │   └── compare_symbols.py         # Compare symbols
│   │
│   ├── decision/              # Decision logic
│   │   ├── rules.py           # Decision rules
│   │   ├── actions.py         # Operator action decider
│   │   └── severity.py        # Error severity logic
│   │
│   ├── annotator/             # Annotation và evidence
│   │   ├── draw_boxes.py      # Draw bounding boxes
│   │   └── save_evidence.py   # Save evidence artifacts
│   │
│   ├── capture/               # Camera capture
│   │   ├── camera_adapter.py      # Camera adapter
│   │   ├── snapshot.py            # Capture snapshot
│   │   ├── metadata_writer.py     # Write metadata
│   │   └── trigger_listener.py    # Listen to triggers
│   │
│   ├── iot/                   # IoT integration
│   │   ├── event_builder.py       # Build IoT events
│   │   ├── callback_client.py     # HTTP callback client
│   │   ├── ack_service.py         # Publish acknowledgment
│   │   └── retry_queue.py         # Retry failed publishes
│   │
│   ├── db/                    # Database layer
│   │   ├── schema.sql         # Database schema
│   │   ├── sqlite.py          # SQLite connection
│   │   └── repositories/      # Data access repositories
│   │       ├── template_repo.py
│   │       ├── scan_result_repo.py
│   │       ├── scan_job_repo.py
│   │       ├── counter_repo.py
│   │       └── iot_event_repo.py
│   │
│   ├── domain/                # Domain models
│   │   ├── enums.py           # Enums (InspectionStatus, etc.)
│   │   ├── models.py          # Domain models
│   │   ├── error_taxonomy.py  # Error taxonomy
│   │   └── decision_schema.py # Decision schemas
│   │
│   ├── counter/               # Counter service
│   │   ├── service.py         # Counter business logic
│   │   └── dedup.py           # Deduplication logic
│   │
│   ├── symbol/                # Symbol recognition
│   │   ├── classify_symbols.py    # Symbol classifier
│   │   ├── postprocess.py         # Symbol postprocessing
│   │   └── remap_taxonomy.py      # Remap symbol taxonomy
│   │
│   ├── utils/                 # Utilities
│   │   ├── config_loader.py   # Load YAML configs
│   │   ├── paths.py           # Path utilities
│   │   ├── json_utils.py      # JSON utilities
│   │   ├── time_utils.py      # Time utilities
│   │   ├── logger.py          # Logging setup
│   │   └── image_utils.py     # Image utilities
│   │
│   └── __init__.py
│
├── tests/                      # Unit tests và integration tests
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── pytest.ini                 # Pytest configuration
├── README.md                  # Project README
└── requirements.txt           # Python dependencies
```

## Mô tả các module chính

### 1. API Layer (`src/api/`)
- **FastAPI application** cung cấp REST API
- **Routes**: Endpoints cho template, inspection, results, IoT, counter
- **Web UI routes**: Render HTML pages cho dashboard

### 2. Web UI (`src/ui/`)
- **HTML templates**: Jinja2 templates cho các pages
- **CSS/JS**: Frontend assets cho interactive UI
- **Services**: Application services xử lý logic cho UI

### 3. Pipeline (`src/pipeline/`)
- **Orchestrator**: Điều phối toàn bộ luồng nghiệp vụ
- **InspectionPipeline**: Pipeline xử lý ảnh và so sánh
- **State machine**: Quản lý trạng thái scan job

### 4. Preprocessing (`src/preprocess/`)
- **Quality gate**: Kiểm tra chất lượng ảnh
- **Crop/Rectify**: Cắt và chỉnh góc
- **Normalize**: Chuẩn hóa ảnh

### 5. OCR (`src/ocr/`)
- **Engine**: PaddleOCR hoặc Tesseract
- **Parser**: Parse kết quả OCR
- **Postprocess**: Làm sạch text

### 6. Comparison (`src/compare/`)
- **Text comparison**: So sánh text fields
- **Symbol comparison**: So sánh care symbols
- **Layout comparison**: So sánh layout
- **Required fields**: Kiểm tra fields bắt buộc

### 7. Decision (`src/decision/`)
- **Rules**: Quy tắc quyết định PASS/FAIL/UNCERTAIN
- **Actions**: Quyết định operator action required
- **Severity**: Tính toán mức độ nghiêm trọng

### 8. Database (`src/db/`)
- **SQLite**: Database lưu trữ
- **Repositories**: Data access layer
- **Schema**: Database schema definition

### 9. IoT Integration (`src/iot/`)
- **Event builder**: Tạo IoT events
- **Callback client**: Gửi HTTP callbacks
- **Retry queue**: Retry failed publishes

### 10. Template Service (`src/template_service/`)
- **Template management**: Upload, review, approve
- **Validation**: Validate template structure
- **Repository**: Template data access

## Luồng dữ liệu chính

```
Camera → Capture → Preprocess → OCR/Symbol Detection
                                        ↓
                                    Compare
                                        ↓
                                    Decision
                                        ↓
                            Save Results + Publish IoT
```

## Luồng nghiệp vụ

```
1. Upload Template → Review → Approve
2. Start Scan Job
3. Inspect Side1 → Confirm
4. Inspect Side2 → Overall Result
5. Publish IoT Event
6. Save to Database
```

## Storage

```
storage/
├── templates/          # Template images và configs
├── captures/           # Ảnh chụp từ camera
├── annotations/        # Evidence artifacts
│   └── {scan_job_id}/
│       ├── side1/
│       │   ├── cam1_aligned.jpg
│       │   ├── cam1_annotated.png
│       │   └── cam1_summary.json
│       └── side2/
└── logs/              # Application logs
```

## Configuration Files

- **app.yaml**: Cấu hình ứng dụng (port, host, debug mode)
- **camera.yaml**: Cấu hình camera (ROI, resolution, exposure)
- **ocr.yaml**: Cấu hình OCR engine (backend, language, confidence)
- **threshold.yaml**: Ngưỡng cho quality gate và comparison
- **iot.yaml**: Cấu hình IoT broker (MQTT/HTTP endpoint)
- **taxonomy_errors.yaml**: Định nghĩa các loại lỗi
- **taxonomy_symbols.yaml**: Định nghĩa các ký hiệu care label

## Database Schema

### Tables chính:
- **templates**: Template definitions
- **scan_jobs**: Scan job tracking
- **side_results**: Side1/Side2 results
- **overall_results**: Overall inspection results
- **iot_events**: IoT publish log
- **counters**: KPI aggregation

## Dependencies chính

- **FastAPI**: Web framework
- **PaddleOCR**: OCR engine
- **OpenCV**: Image processing
- **Pillow**: Image manipulation
- **SQLite**: Database
- **Pydantic**: Data validation
- **Jinja2**: Template engine
- **YAML**: Configuration

## Notes

- Tất cả configs đều dùng YAML format
- Database dùng SQLite cho đơn giản
- Evidence được lưu dạng file (ảnh + JSON)
- IoT integration hỗ trợ cả MQTT và HTTP
- Web UI dùng vanilla JS, không dùng framework nặng
