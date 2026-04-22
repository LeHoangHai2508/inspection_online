# Implementation: Multi-Language OCR Selection

## ✅ Bước 1: Domain Models - HOÀN TẤT

Đã thêm `ocr_languages` vào:
- `TemplateRecord.ocr_languages: list[str]`
- `TemplateUploadRequest.ocr_languages: list[str]`

## Bước 2: Database Schema

### 2.1. Sửa schema.sql

File: `src/db/schema.sql`

Thêm cột `ocr_languages_json`:

```sql
CREATE TABLE IF NOT EXISTS templates (
    template_id TEXT PRIMARY KEY,
    template_name TEXT NOT NULL,
    product_code TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    review_notes TEXT DEFAULT '',
    ocr_languages_json TEXT DEFAULT '["en","vi"]'
);
```

### 2.2. Migration (nếu DB đã tồn tại)

```bash
# Stop server
# Backup DB
cp data/sqlite/inspection.db data/sqlite/inspection.db.backup

# Run migration
python -c "
import sqlite3
conn = sqlite3.connect('data/sqlite/inspection.db')
cursor = conn.cursor()
cursor.execute('ALTER TABLE templates ADD COLUMN ocr_languages_json TEXT DEFAULT \'[\"en\",\"vi\"]\'')
conn.commit()
conn.close()
print('Migration completed!')
"
```

Hoặc đơn giản hơn (nếu dev local):
```bash
# Xóa DB cũ và tạo lại
rm data/sqlite/inspection.db
python scripts/init_sqlite.py
```

## Bước 3: API Schema

File: `src/api/schemas.py`

Cần tìm và sửa `TemplateUploadPayload`:

```python
@dataclass(frozen=True)
class TemplateUploadPayload:
    template_name: str
    product_code: str
    created_by: str
    side1_file: TemplateUploadFile
    side2_file: TemplateUploadFile
    ocr_languages: list[str]  # THÊM DÒNG NÀY

    def to_command(self) -> TemplateUploadRequest:
        return TemplateUploadRequest(
            template_name=self.template_name,
            product_code=self.product_code,
            created_by=self.created_by,
            side1_file=self.side1_file,
            side2_file=self.side2_file,
            ocr_languages=self.ocr_languages,  # THÊM DÒNG NÀY
        )
```

## Bước 4: Upload Route

File: `src/api/routes/templates.py`

Sửa route `/upload` để nhận `ocr_languages_csv`:

```python
@router.post("/upload")
async def upload_template(
    template_name: str = Form(...),
    product_code: str = Form(...),
    created_by: str = Form(...),
    ocr_languages_csv: str = Form("en,vi"),  # THÊM DÒNG NÀY
    side1_file: Optional[UploadFile] = File(None),
    side2_file: Optional[UploadFile] = File(None),
    combined_file: Optional[UploadFile] = File(None),
    container: ApplicationContainer = Depends(get_container),
):
    try:
        # Parse CSV to list
        selected_languages = [
            item.strip()
            for item in ocr_languages_csv.split(",")
            if item.strip()
        ]
        
        if not selected_languages:
            raise ValueError("ocr_languages_csv must contain at least one language")
        
        # ... xử lý combined_file / side1_file / side2_file như cũ ...
        
        payload = TemplateUploadPayload(
            template_name=template_name,
            product_code=product_code,
            created_by=created_by,
            side1_file=side1_upload,
            side2_file=side2_upload,
            ocr_languages=selected_languages,  # THÊM DÒNG NÀY
        )
        
        record = container.template_service.create_draft(payload.to_command())
        return to_primitive(record)
    except Exception as exc:
        # ... error handling ...
```

## Bước 5: Repository

File: `src/db/repositories/template_repo.py`

### 5.1. Sửa save template

Tìm phần `INSERT INTO templates` và thêm `ocr_languages_json`:

```python
import json

cursor.execute(
    """
    INSERT INTO templates (
        template_id, template_name, product_code, status, 
        created_by, created_at, review_notes, ocr_languages_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(template_id) DO UPDATE SET
        template_name=excluded.template_name,
        product_code=excluded.product_code,
        status=excluded.status,
        review_notes=excluded.review_notes,
        ocr_languages_json=excluded.ocr_languages_json
    """,
    (
        record.template_id,
        record.template_name,
        record.product_code,
        record.status.value,
        record.created_by,
        record.created_at.isoformat(),
        record.review_notes,
        json.dumps(record.ocr_languages, ensure_ascii=False),  # THÊM DÒNG NÀY
    ),
)
```

### 5.2. Sửa load template

Tìm phần build `TemplateRecord` và thêm `ocr_languages`:

```python
return TemplateRecord(
    template_id=template_row["template_id"],
    template_version=version,
    template_name=template_row["template_name"],
    product_code=template_row["product_code"],
    created_by=template_row["created_by"],
    status=TemplateStatus(template_row["status"]),
    sides=sides,
    ocr_languages=json.loads(
        template_row.get("ocr_languages_json") or '["en","vi"]'
    ),  # THÊM DÒNG NÀY
    approved_by=template_row.get("approved_by"),
    created_at=datetime.fromisoformat(template_row["created_at"]),
    review_notes=template_row.get("review_notes") or "",
)
```

## Bước 6: OCR Workflow

File: `src/ocr/run_ocr.py`

### 6.1. Sửa run_template_ocr

```python
def run_template_ocr(
    self,
    side: InspectionSide,
    file: TemplateUploadFile,
    ocr_languages: list[str] | None = None,  # THÊM PARAMETER
) -> tuple[OCRDocument, list]:
    document = self._engine.run(
        side=side,
        file=file,
        ocr_languages=ocr_languages,  # TRUYỀN VÀO ENGINE
    )
    return document, extract_candidate_fields(side=side, blocks=document.blocks)
```

### 6.2. Sửa run_capture_ocr

```python
def run_capture_ocr(
    self,
    side: InspectionSide,
    capture: CaptureInput,
    ocr_languages: list[str] | None = None,  # THÊM PARAMETER
) -> tuple[str, list, list[ObservedField]]:
    document = self._engine.run(
        side=side,
        file=TemplateUploadFile(
            filename=capture.filename,
            content=capture.content,
            media_type=capture.media_type,
        ),
        ocr_languages=ocr_languages,  # TRUYỀN VÀO ENGINE
    )
    # ... rest of the code ...
```

## Bước 7: Template Service

File: `src/template_service/service.py`

### 7.1. Sửa _build_side_definition

Tìm chỗ gọi `run_template_ocr` và thêm `ocr_languages`:

```python
def _build_side_definition(
    self,
    side: InspectionSide,
    upload_file: TemplateUploadFile,
    upload_request: TemplateUploadRequest,  # Cần có parameter này
) -> TemplateSideDefinition:
    document, extracted_fields = self._ocr_workflow.run_template_ocr(
        side=side,
        file=upload_file,
        ocr_languages=upload_request.ocr_languages,  # THÊM DÒNG NÀY
    )
    # ... rest of the code ...
```

### 7.2. Sửa create_draft

Thêm `ocr_languages` khi tạo `TemplateRecord`:

```python
record = TemplateRecord(
    template_id=template_id,
    template_version=template_version,
    template_name=request.template_name.strip(),
    product_code=request.product_code.strip(),
    created_by=request.created_by.strip(),
    status=TemplateStatus.REVIEW_REQUIRED,
    sides={
        InspectionSide.SIDE1: side1_definition,
        InspectionSide.SIDE2: side2_definition,
    },
    ocr_languages=request.ocr_languages,  # THÊM DÒNG NÀY
)
```

## Bước 8: Inspection Pipeline

File: `src/pipeline/inspection_pipeline.py`

Tìm chỗ gọi `run_capture_ocr` và thêm `ocr_languages`:

```python
raw_text, blocks, observed_fields = self._ocr_workflow.run_capture_ocr(
    side=inspection_input.side,
    capture=normalized_capture,
    ocr_languages=template.ocr_languages,  # THÊM DÒNG NÀY
)
```

## Bước 9: AutoOCREngine (ĐÃ HOÀN TẤT)

File `src/ocr/engine.py` đã được refactor với:
- ✅ Cache engine theo ngôn ngữ
- ✅ Thread lock để tránh build đôi
- ✅ Dynamic languages từ user input
- ✅ Bỏ CUDA_VISIBLE_DEVICES=-1

## Bước 10: UI - Template Upload Form

File: `src/ui/templates/template_upload.html` (hoặc tương tự)

Thêm multi-select cho ngôn ngữ:

```html
<div class="form-group">
    <label for="ocr_languages">OCR Languages (Ctrl+Click to select multiple)</label>
    <select id="ocr_languages" class="form-control" multiple size="10">
        <option value="en" selected>English (en)</option>
        <option value="vi" selected>Vietnamese (vi)</option>
        <option value="fr">French (fr)</option>
        <option value="de">German (de)</option>
        <option value="it">Italian (it)</option>
        <option value="es">Spanish (es)</option>
        <option value="pt">Portuguese (pt)</option>
        <option value="ru">Russian (ru)</option>
        <option value="ar">Arabic (ar)</option>
        <option value="ch_sim">Chinese Simplified (ch_sim)</option>
        <option value="ch_tra">Chinese Traditional (ch_tra)</option>
        <option value="ja">Japanese (ja)</option>
        <option value="ko">Korean (ko)</option>
        <option value="th">Thai (th)</option>
    </select>
    <input type="hidden" name="ocr_languages_csv" id="ocr_languages_csv" value="en,vi">
    <small class="form-text text-muted">
        Select languages that appear on your garment labels. 
        More languages = slower OCR but better accuracy.
    </small>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const select = document.getElementById('ocr_languages');
    const hidden = document.getElementById('ocr_languages_csv');
    
    // Update hidden field before submit
    form.addEventListener('submit', function(e) {
        const selected = Array.from(select.selectedOptions).map(opt => opt.value);
        if (selected.length === 0) {
            alert('Please select at least one language');
            e.preventDefault();
            return false;
        }
        hidden.value = selected.join(',');
    });
});
</script>
```

## Testing

### Test 1: Upload template với ngôn ngữ tùy chỉnh

1. Vào `/templates/upload`
2. Chọn ngôn ngữ: en, vi, fr, de, es
3. Upload template
4. Kiểm tra log:
```
[AutoOCR] Building new engine: easyocr:de,en,es,fr,vi
[EasyOCR] Initializing with GPU=True, langs=['de', 'en', 'es', 'fr', 'vi']
```

### Test 2: Upload template thứ 2 với cùng ngôn ngữ

1. Upload template khác với cùng 5 ngôn ngữ
2. Kiểm tra log:
```
[AutoOCR] Using cached engine: easyocr:de,en,es,fr,vi
```

### Test 3: Runtime inspection

1. Inspect với template đã tạo
2. Kiểm tra log phải dùng đúng ngôn ngữ của template

## Rollback Plan

Nếu có vấn đề, rollback theo thứ tự ngược:

1. Restore `src/ocr/engine.py` từ backup
2. Restore DB: `cp data/sqlite/inspection.db.backup data/sqlite/inspection.db`
3. Git revert các file đã sửa

## Performance Expectations

| Languages | Init Time | OCR Time | RAM |
|-----------|-----------|----------|-----|
| 2 (en, vi) | 8-10s | 2-3s | 2GB |
| 5 (en, vi, fr, de, es) | 12-15s | 3-4s | 3GB |
| 10+ | 20-25s | 4-5s | 4-5GB |

## Khuyến nghị

- **Mặc định**: en, vi (nhanh nhất)
- **EU labels**: en, vi, fr, de, it, es, pt
- **Asian labels**: en, ch_sim, ja, ko
- **Arabic labels**: en, ar

Không nên chọn quá 7-8 ngôn ngữ trừ khi thực sự cần thiết.
