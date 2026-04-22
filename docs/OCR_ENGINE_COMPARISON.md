# So sánh các OCR Engine

## Tổng quan

| Engine | Tốc độ | Độ chính xác | RAM | GPU | Ngôn ngữ | Khuyến nghị |
|--------|--------|--------------|-----|-----|----------|-------------|
| **Tesseract** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 200MB | ❌ | 100+ | Dev/Test |
| **PaddleOCR** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 500MB | ✅ | 80+ | **Production** |
| **EasyOCR** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 1-6GB | ✅ | 80+ | High accuracy |
| **Ensemble** | ⭐⭐ | ⭐⭐⭐⭐⭐ | 6-8GB | ✅ | 80+ | Critical cases |

## Chi tiết

### 1. Tesseract

**Ưu điểm:**
- ✅ Nhanh nhất (< 1s/ảnh)
- ✅ Nhẹ nhất (200MB RAM)
- ✅ Miễn phí, mã nguồn mở
- ✅ Hỗ trợ 100+ ngôn ngữ
- ✅ Không cần GPU

**Nhược điểm:**
- ❌ Độ chính xác thấp với ảnh chất lượng kém
- ❌ Kém với chữ nhỏ, nghiêng, cong
- ❌ Cần preprocessing tốt

**Khi nào dùng:**
- Dev/test local
- Ảnh chất lượng tốt, chữ rõ ràng
- Không cần độ chính xác cao

**Cấu hình:**
```yaml
engine: tesseract
gpu: false
```

---

### 2. PaddleOCR (Khuyến nghị cho Production)

**Ưu điểm:**
- ✅ Cân bằng tốc độ và độ chính xác
- ✅ Hỗ trợ 80+ ngôn ngữ
- ✅ Có thể dùng CPU hoặc GPU
- ✅ RAM vừa phải (500MB)
- ✅ Tốt với chữ Trung, Nhật, Hàn

**Nhược điểm:**
- ⚠️ Chậm hơn Tesseract (1-2s/ảnh)
- ⚠️ Cần cài PaddlePaddle framework

**Khi nào dùng:**
- **Production environment** (khuyến nghị)
- Cần độ chính xác cao
- Có nhiều ngôn ngữ châu Á
- Máy không có GPU hoặc GPU yếu

**Cấu hình:**
```yaml
engine: paddleocr
gpu: false  # hoặc true nếu có GPU
```

**Cài đặt:**
```bash
pip install paddlepaddle paddleocr
```

---

### 3. EasyOCR

**Ưu điểm:**
- ✅ Độ chính xác cao nhất (single engine)
- ✅ Tốt với nhiều font chữ, góc nghiêng
- ✅ Hỗ trợ 80+ ngôn ngữ
- ✅ API đơn giản

**Nhược điểm:**
- ❌ Chậm nhất (3-5s/ảnh)
- ❌ Tốn RAM nhiều (1-6GB tùy số ngôn ngữ)
- ❌ Khởi tạo lâu (15-30s với nhiều ngôn ngữ)
- ❌ Cần GPU để nhanh

**Khi nào dùng:**
- Cần độ chính xác cao nhất
- Có GPU mạnh (GTX 1650+)
- Không quan trọng tốc độ
- Ảnh chất lượng kém, chữ nhỏ, nghiêng

**Cấu hình:**
```yaml
engine: easyocr
gpu: true

# CHỈ THÊM NGÔN NGỮ CẦN THIẾT
easyocr_langs:
  - en
  - fr
  - de
  - ch_sim
```

**Tối ưu:**
- Giảm số ngôn ngữ xuống còn 4-6 ngôn ngữ thực sự cần
- Mỗi ngôn ngữ thêm = +300MB RAM + +2s khởi tạo

**Cài đặt:**
```bash
# Với GPU
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install easyocr

# Không GPU
pip install easyocr
```

---

### 4. Ensemble (EasyOCR + KerasOCR)

**Ưu điểm:**
- ✅ Độ chính xác cao nhất (2 engines)
- ✅ Tự động verify các block khó
- ✅ Tốt với Arabic, CJK ở cuối ảnh

**Nhược điểm:**
- ❌ Chậm nhất (5-8s/ảnh)
- ❌ Tốn RAM nhất (6-8GB)
- ❌ Phức tạp nhất
- ❌ Bắt buộc cần GPU

**Khi nào dùng:**
- Critical inspection (không được phép sai)
- Có GPU mạnh + RAM nhiều
- Ảnh rất khó (chữ nhỏ, nhiều ngôn ngữ, chất lượng kém)

**Cấu hình:**
```yaml
engine: ensemble
gpu: true

easyocr_langs:
  - en
  - fr
  - de

verifier:
  enabled: true
  min_confidence_to_skip: 0.82
```

**Cài đặt:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install easyocr keras-ocr tensorflow
```

---

## Khuyến nghị theo use case

### Use case 1: Dev/Test local
```yaml
engine: tesseract
gpu: false
```

### Use case 2: Production (khuyến nghị)
```yaml
engine: paddleocr
gpu: false
```

### Use case 3: High accuracy, có GPU
```yaml
engine: easyocr
gpu: true
easyocr_langs:
  - en
  - fr
  - de
  - ch_sim
```

### Use case 4: Critical inspection
```yaml
engine: ensemble
gpu: true
easyocr_langs:
  - en
  - fr
  - de
verifier:
  enabled: true
```

---

## Benchmark thực tế

Test với ảnh tem 2 mặt (1200x1600px):

| Engine | Khởi tạo | Side1 | Side2 | Tổng | RAM |
|--------|----------|-------|-------|------|-----|
| Tesseract | 0.5s | 0.8s | 1.2s | 2.5s | 200MB |
| PaddleOCR | 2s | 1.5s | 2.0s | 5.5s | 500MB |
| EasyOCR (6 langs) | 8s | 3.0s | 3.5s | 14.5s | 2GB |
| EasyOCR (14 langs) | 25s | 3.5s | 4.0s | 32.5s | 5GB |
| Ensemble (6 langs) | 15s | 5.0s | 6.0s | 26s | 6GB |

**Kết luận:** PaddleOCR là lựa chọn tốt nhất cho production.

---

## Cách chuyển đổi engine

### Từ EasyOCR sang PaddleOCR (nhanh hơn)

1. Sửa `configs/ocr.yaml`:
```yaml
engine: paddleocr
gpu: false
```

2. Cài PaddleOCR:
```bash
pip install paddlepaddle paddleocr
```

3. Restart server

### Từ PaddleOCR sang EasyOCR (chính xác hơn)

1. Sửa `configs/ocr.yaml`:
```yaml
engine: easyocr
gpu: true
easyocr_langs:
  - en
  - fr
  - de
  - ch_sim
```

2. Cài EasyOCR:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install easyocr
```

3. Restart server

---

## FAQ

**Q: Tại sao EasyOCR chậm?**
A: Vì load nhiều deep learning models. Giảm số ngôn ngữ xuống 4-6 để nhanh hơn.

**Q: Có thể dùng EasyOCR không GPU?**
A: Có, nhưng sẽ chậm hơn 3-5 lần. Khuyến nghị dùng PaddleOCR thay thế.

**Q: Engine nào tốt nhất?**
A: PaddleOCR cho production, EasyOCR nếu cần độ chính xác cao và có GPU.

**Q: Có thể mix nhiều engine?**
A: Có, dùng `engine: ensemble` để kết hợp EasyOCR + KerasOCR.
