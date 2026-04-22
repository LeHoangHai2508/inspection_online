# Hướng dẫn cài Tesseract OCR trên Windows

## Bước 1: Download Tesseract
1. Truy cập: https://github.com/UB-Mannheim/tesseract/wiki
2. Download bản mới nhất (ví dụ: tesseract-ocr-w64-setup-5.3.3.20231005.exe)
3. Chạy installer

## Bước 2: Cài đặt
1. Chọn đường dẫn cài đặt (mặc định: `C:\Program Files\Tesseract-OCR`)
2. **QUAN TRỌNG**: Trong bước chọn components, chọn thêm:
   - Additional language data (jpn, rus, chi_sim nếu cần đọc tiếng Nhật/Nga/Trung)
3. Hoàn tất cài đặt

## Bước 3: Thêm vào PATH
1. Mở System Properties → Environment Variables
2. Trong System Variables, tìm biến `Path`
3. Thêm đường dẫn: `C:\Program Files\Tesseract-OCR`
4. Click OK

## Bước 4: Kiểm tra
Mở PowerShell mới và chạy:
```bash
tesseract --version
```

Nếu thấy version hiện ra là OK.

## Bước 5: Cài pytesseract (optional, nhưng khuyến nghị)
```bash
.venv/Scripts/pip install pytesseract
```

## Bước 6: Restart server và test
```bash
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Upload template lại - lần này sẽ dùng Tesseract thay vì PaddleOCR.

---

## Nếu không muốn cài Tesseract ngay

Có thể tạm thời bỏ qua OCR để test workflow:

**Sửa `configs/ocr.yaml`:**
```yaml
engine: auto
strict_real_ocr: false
```

Nhưng lưu ý: với config này, nếu không có OCR thật, hệ thống sẽ báo lỗi rõ ràng thay vì sinh text rác (nhờ fix MockOCREngine).
