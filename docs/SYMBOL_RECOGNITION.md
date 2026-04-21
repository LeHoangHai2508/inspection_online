# Hướng dẫn Symbol Recognition

## Tổng quan

Hệ thống nhận dạng care symbols đã được tách riêng khỏi OCR text branch để xử lý chính xác hơn.

## Kiến trúc

```
Runtime Capture
    ↓
    ├─→ OCR Text Branch (Tesseract/Paddle)
    │   └─→ extract_runtime_observed_fields()
    │       └─→ text_fields (field: value format)
    │
    └─→ Symbol Branch
        ├─→ detect_symbol_regions() 
        │   └─→ contour detection + filtering
        ├─→ classify_symbol()
        │   └─→ template matching (hoặc ML model)
        └─→ symbol_fields (care_symbols field)
    
    ↓
Merge text_fields + symbol_fields
    ↓
Compare với template
```

## Các thay đổi chính

### 1. OCR Preprocessing (src/ocr/engine.py)

**Đã sửa:**
- Bỏ denoise mặc định (tránh mất nét chữ nhỏ)
- Sửa scale từ fx=1.0, fy=1.0 → fx=2.0, fy=2.0 cho side2
- Thay đổi PSM mode:
  - Side1: PSM 6 (uniform text block)
  - Side2: PSM 4 (single column of text)
- Thêm tham số `use_denoise` để kiểm soát denoise

**Lý do:**
- Denoise làm mất chi tiết chữ nhỏ và dấu câu
- Scale 2x giúp Tesseract đọc chữ nhỏ tốt hơn
- PSM 6/4 phù hợp hơn với layout nhãn mác

### 2. Symbol Detection (src/symbol/detect_symbols.py)

**Cách hoạt động:**
1. Đọc ảnh grayscale
2. Threshold Otsu để lấy nét icon
3. Tìm contours
4. Lọc theo kích thước:
   - Bỏ nhiễu nhỏ (< 12x12 pixels)
   - Bỏ contour quá to (> 50% ảnh)
   - Giữ area >= 200 pixels
5. Sort theo vị trí (trái → phải, trên → dưới)

**Tham số có thể điều chỉnh:**
```python
# Trong detect_symbols.py
MIN_SIZE = 12  # pixels
MAX_SIZE_RATIO = 0.5  # % of image
MIN_AREA = 200  # pixels²
```

### 3. Symbol Classification (src/symbol/classify_symbols.py)

**Phương pháp hiện tại: Template Matching**

1. Normalize cả query và template về 64x64
2. Threshold Otsu
3. cv2.matchTemplate với TM_CCOEFF_NORMED
4. Chọn template có score cao nhất
5. Threshold: score >= 0.65

**Cấu trúc template:**
```
assets/symbol_templates/
  wash_30/
    template1.png
    template2.png
  do_not_bleach/
    template1.png
  ...
```

**Khi nào cần nâng cấp lên ML:**
- Template matching score thấp
- Symbol bị nghiêng/méo nhiều
- Nền thay đổi phức tạp
- Cần phát hiện symbol mới tự động

### 4. Symbol Workflow (src/symbol/run_symbol.py)

**Flow:**
1. Detect tất cả symbol regions
2. Classify từng region
3. Lọc kết quả (score >= 0.65)
4. Merge thành 1 field `care_symbols`
5. Value format: `wash_30|do_not_bleach|iron_low`

**Output:**
```python
ObservedField(
    field_name="care_symbols",
    value="wash_30|do_not_bleach|iron_low",
    confidence=0.85,  # average của tất cả symbols
    bbox=merged_bbox,  # bounding box bao tất cả symbols
    camera_source=capture.camera_id,
)
```

### 5. OCR Workflow Integration (src/ocr/run_ocr.py)

**Đã thêm:**
```python
class OCRWorkflow:
    def __init__(
        self,
        engine: AutoOCREngine | None = None,
        symbol_workflow: SymbolWorkflow | None = None,
    ):
        self._engine = engine or AutoOCREngine()
        self._symbol_workflow = symbol_workflow or SymbolWorkflow()
```

**Flow mới:**
```python
def run_capture_ocr(self, side, capture):
    # 1. OCR text
    document = self._engine.run(side, file)
    text_fields = extract_runtime_observed_fields(document.blocks)
    
    # 2. Symbol detection
    symbol_fields = self._symbol_workflow.run_capture_symbol(capture)
    
    # 3. Merge
    observed_fields = text_fields + symbol_fields
    return document.raw_text, document.blocks, observed_fields
```

### 6. Symbol Comparison (src/compare/compare_symbols.py)

**Đã sửa từ string comparison sang set comparison:**

```python
def compare_symbol_value(expected_value: str, actual_value: str) -> bool:
    expected = {item.strip().upper() for item in expected_value.split("|") if item.strip()}
    actual = {item.strip().upper() for item in actual_value.split("|") if item.strip()}
    return expected == actual
```

**Ví dụ:**
- Expected: `wash_30|do_not_bleach|iron_low`
- Actual: `iron_low|wash_30|do_not_bleach`
- Result: ✅ PASS (thứ tự không quan trọng)

## Cách sử dụng

### 1. Thêm template symbols

```bash
# Tạo thư mục cho symbol mới
mkdir assets/symbol_templates/wash_60

# Thêm 2-5 ảnh template
# - Kích thước: 64x64 đến 128x128
# - Format: PNG hoặc JPG
# - Nền trắng hoặc trong suốt
```

### 2. Tạo template field cho symbols

Trong template review, thêm field:

```json
{
  "field_name": "care_symbols",
  "expected_value": "wash_30|do_not_bleach|iron_low",
  "compare_type": "symbol_match",
  "priority": "critical",
  "required": true
}
```

### 3. Runtime inspection

Hệ thống tự động:
1. Detect symbols từ ảnh
2. Classify từng symbol
3. Merge thành field `care_symbols`
4. Compare với template

## Troubleshooting

### Symbol không được phát hiện

**Nguyên nhân:**
- Contour quá nhỏ hoặc quá to
- Threshold không phù hợp

**Giải pháp:**
```python
# Điều chỉnh trong detect_symbols.py
MIN_SIZE = 10  # giảm nếu symbol nhỏ
MIN_AREA = 150  # giảm nếu symbol nhỏ
```

### Classification sai

**Nguyên nhân:**
- Template không đủ đa dạng
- Symbol bị nghiêng/méo
- Score threshold quá thấp

**Giải pháp:**
1. Thêm nhiều template cho class đó
2. Thêm augmented templates (xoay, scale)
3. Tăng threshold:
```python
# Trong run_symbol.py
if label == "unknown" or score < 0.75:  # tăng từ 0.65
    continue
```

### Symbol bị merge sai

**Nguyên nhân:**
- Nhiều symbols gần nhau
- Contour detection không tách được

**Giải pháp:**
- Điều chỉnh threshold trong detect
- Sử dụng morphological operations
- Nâng cấp lên object detection model

## Nâng cấp lên ML Model

### Khi nào cần train model?

- Template matching accuracy < 85%
- Symbol có nhiều biến thể
- Cần phát hiện symbol mới tự động
- Cần xử lý symbol bị che khuất/méo

### Dataset structure

```
datasets/symbols/
  train/
    wash_30/
      img001.png
      img002.png
      ...
    wash_40/
      ...
    do_not_bleach/
      ...
  val/
    wash_30/
      ...
```

### Model options

**1. Classifier only (nếu detection tốt):**
```python
# ResNet18, MobileNetV2, EfficientNet
from torchvision.models import resnet18
model = resnet18(pretrained=True)
model.fc = nn.Linear(512, num_classes)
```

**2. Detection + Classification:**
```python
# YOLOv8, Faster R-CNN
from ultralytics import YOLO
model = YOLO('yolov8n-cls.pt')
model.train(data='datasets/symbols', epochs=50)
```

### Thay thế classify_symbols.py

```python
# src/symbol/classify_symbols.py
import torch
from torchvision import transforms

model = torch.load('models/symbol_classifier.pt')
transform = transforms.Compose([...])

def classify_symbol(img: np.ndarray) -> Tuple[str, float]:
    tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        output = model(tensor)
        probs = torch.softmax(output, dim=1)
        score, idx = probs.max(1)
    return class_names[idx], score.item()
```

## Testing

```python
# Test symbol detection
from src.symbol.detect_symbols import detect_symbol_regions
from src.domain.models import CaptureInput

capture = CaptureInput(...)
regions = detect_symbol_regions(capture)
print(f"Found {len(regions)} symbols")

# Test classification
from src.symbol.classify_symbols import classify_symbol
for region in regions:
    label, score = classify_symbol(region.image)
    print(f"{label}: {score:.2f}")

# Test full workflow
from src.symbol.run_symbol import SymbolWorkflow
workflow = SymbolWorkflow()
fields = workflow.run_capture_symbol(capture)
print(fields)
```

## Performance

**Template Matching:**
- Speed: ~10-50ms per symbol
- Accuracy: 70-90% (depends on templates)
- Memory: Low (~10MB)

**ML Model (CNN):**
- Speed: ~5-20ms per symbol (GPU)
- Accuracy: 90-98%
- Memory: Medium (~50-200MB)

**ML Model (YOLO):**
- Speed: ~20-100ms per image (all symbols)
- Accuracy: 92-99%
- Memory: High (~200-500MB)

## Roadmap

- [ ] Thêm augmentation cho template matching
- [ ] Implement confidence calibration
- [ ] Train baseline CNN classifier
- [ ] Collect production data for fine-tuning
- [ ] A/B test template vs ML approach
- [ ] Add symbol detection metrics to monitoring
