# Symbol Templates

Thư mục này chứa các template ảnh cho việc nhận dạng care symbols.

## Cấu trúc

Mỗi class symbol nên có một thư mục riêng với tên là label của symbol đó:

```
assets/symbol_templates/
  wash_30/
    template1.png
    template2.png
  wash_40/
    template1.png
  do_not_bleach/
    template1.png
    template2.png
  do_not_tumble_dry/
    template1.png
  iron_low/
    template1.png
  dry_flat/
    template1.png
  ...
```

## Hướng dẫn thêm template

1. Tạo thư mục mới với tên là label của symbol (ví dụ: `wash_30`, `do_not_bleach`)
2. Thêm 2-5 ảnh mẫu của symbol đó vào thư mục
3. Ảnh nên:
   - Có nền trắng hoặc trong suốt
   - Kích thước khoảng 64x64 đến 128x128 pixels
   - Định dạng PNG hoặc JPG
   - Chứa symbol rõ ràng, không bị che khuất

## Cách hoạt động

Hệ thống sử dụng template matching để so sánh symbol phát hiện được với các template:
- Normalize cả query và template về 64x64 pixels
- Áp dụng threshold để có ảnh nhị phân
- Sử dụng cv2.matchTemplate với TM_CCOEFF_NORMED
- Chọn template có score cao nhất (> 0.65)

## Nâng cấp lên ML model

Khi template matching không đủ chính xác, bạn có thể:

1. **Tạo dataset training**:
   ```
   datasets/symbols/
     train/
       wash_30/
       wash_40/
       do_not_bleach/
       ...
     val/
       wash_30/
       wash_40/
       ...
   ```

2. **Train classifier** (CNN hoặc transfer learning):
   - ResNet18/MobileNetV2 cho classification
   - YOLO/Faster R-CNN nếu cần detection + classification

3. **Thay thế classify_symbols.py** với model đã train

## Các symbol phổ biến

- `wash_30`, `wash_40`, `wash_60` - Giặt ở nhiệt độ
- `do_not_wash` - Không giặt
- `hand_wash` - Giặt tay
- `bleach` - Tẩy được
- `do_not_bleach` - Không tẩy
- `tumble_dry` - Sấy khô
- `do_not_tumble_dry` - Không sấy khô
- `iron_low`, `iron_medium`, `iron_high` - Ủi ở nhiệt độ
- `do_not_iron` - Không ủi
- `dry_flat` - Phơi phẳng
- `hang_dry` - Phơi treo
- `dry_clean` - Giặt khô
- `do_not_dry_clean` - Không giặt khô
