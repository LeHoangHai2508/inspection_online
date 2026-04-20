from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class SplitSideImage:
    side_name: str
    content: bytes
    media_type: str
    filename: str
    width: int
    height: int


@dataclass(frozen=True)
class RectoVersoSplitResult:
    side1: SplitSideImage
    side2: SplitSideImage


class RectoVersoSplitter:
    """
    Tách 1 ảnh template chứa cả recto + verso thành 2 ảnh side1/side2.

    Giả định hiện tại:
    - 2 panel nằm trái/phải
    - ảnh đầu vào là 1 ảnh scan/chụp chứa đủ 2 panel
    - nếu OCR header không đọc được, fallback: trái=side1, phải=side2
    """

    def split(
        self,
        image_bytes: bytes,
        filename: str = "combined_template.jpg",
        media_type: str = "image/jpeg",
    ) -> RectoVersoSplitResult:
        image = self._decode_image(image_bytes)
        h, w = image.shape[:2]

        # Luôn cắt dọc (vertical split) - trái/phải
        split_x = self._find_vertical_split(image)
        
        left = image[:, :split_x]
        right = image[:, split_x:]
        
        left = self._trim_panel(left)
        right = self._trim_panel(right)
        
        side1_img, side2_img = self._assign_sides(left, right)
        
        # Xoay 180 độ chỉ side1
        side1_img = cv2.rotate(side1_img, cv2.ROTATE_180)

        side1_bytes = self._encode_jpg(side1_img)
        side2_bytes = self._encode_jpg(side2_img)

        side1_h, side1_w = side1_img.shape[:2]
        side2_h, side2_w = side2_img.shape[:2]

        return RectoVersoSplitResult(
            side1=SplitSideImage(
                side_name="side1",
                content=side1_bytes,
                media_type=media_type,
                filename=f"{Path(filename).stem}_side1.jpg",
                width=side1_w,
                height=side1_h,
            ),
            side2=SplitSideImage(
                side_name="side2",
                content=side2_bytes,
                media_type=media_type,
                filename=f"{Path(filename).stem}_side2.jpg",
                width=side2_w,
                height=side2_h,
            ),
        )

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError("Cannot decode combined template image.")
        return image

    def _find_vertical_split(self, image: np.ndarray) -> int:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Nhị phân hóa để tìm vùng có ít nội dung gần giữa ảnh
        _, thresh = cv2.threshold(
            blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        column_density = thresh.sum(axis=0).astype(np.float32)

        h, w = image.shape[:2]
        center_start = int(w * 0.35)
        center_end = int(w * 0.65)

        center_slice = column_density[center_start:center_end]
        best_local = int(np.argmin(center_slice))
        split_x = center_start + best_local

        return split_x

    def _find_horizontal_split(self, image: np.ndarray) -> int:
        """Tìm đường chia ngang cho layout dọc (2 panel trên/dưới)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Nhị phân hóa để tìm vùng có ít nội dung gần giữa ảnh
        _, thresh = cv2.threshold(
            blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        row_density = thresh.sum(axis=1).astype(np.float32)

        h, w = image.shape[:2]
        center_start = int(h * 0.35)
        center_end = int(h * 0.65)

        center_slice = row_density[center_start:center_end]
        best_local = int(np.argmin(center_slice))
        split_y = center_start + best_local

        return split_y

    def _trim_panel(self, panel: np.ndarray) -> np.ndarray:
        """Trim viền trắng"""
        gray = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

        coords = cv2.findNonZero(thresh)
        if coords is None:
            return panel

        x, y, w, h = cv2.boundingRect(coords)
        trimmed = panel[y:y+h, x:x+w]
        
        return trimmed

    def _assign_sides(self, left: np.ndarray, right: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Layout cố định: trái = side1, phải = side2
        Không OCR header để tăng tốc độ
        """
        return left, right

    def _encode_jpg(self, image: np.ndarray) -> bytes:
        ok, buf = cv2.imencode(".jpg", image)
        if not ok:
            raise RuntimeError("Cannot encode split image.")
        return buf.tobytes()
