"""
Template Application Service
────────────────────────────────────────────────────────────────────────────────
Service lớp ứng dụng cho quản lý template — lớp trung gian giữa web controller
và domain service, giúp controller không phải biết chi tiết domain logic.

Chức năng chính:
- Upload template mới (ảnh side1 + side2)
- OCR full template và tạo preview
- Review và chỉnh sửa field
- Approve/reject template
"""
from __future__ import annotations

from src.api.serializers import to_primitive
from src.template_service.service import TemplateService


class TemplateAppService:
    """
    Application service cho template lifecycle.
    
    Đây là lớp facade mỏng giữa web routes và domain service, giúp:
    - Controller không cần biết chi tiết domain model
    - Tự động serialize domain object thành dict/JSON
    - Tập trung xử lý lỗi và validation ở một chỗ
    """

    def __init__(self, template_service: TemplateService) -> None:
        """
        Khởi tạo service với template domain service.
        
        Args:
            template_service: Domain service xử lý logic template
        """
        self._svc = template_service

    def upload_and_draft(self, request) -> dict:
        """
        Upload template mới và tạo bản draft.
        
        Luồng xử lý:
        1. Nhận file ảnh side1 + side2 từ request
        2. OCR full cả 2 mặt
        3. Tạo template record với status = DRAFT
        4. Trả về template_id và metadata
        
        Args:
            request: TemplateUploadRequest chứa file ảnh và metadata
            
        Returns:
            dict: Template record đã serialize, bao gồm:
                - template_id: ID duy nhất của template
                - status: DRAFT
                - side1/side2 OCR text và blocks
                
        Raises:
            ValueError: Nếu file không hợp lệ hoặc thiếu thông tin bắt buộc
        """
        record = self._svc.create_draft(request)
        return to_primitive(record)

    def get_preview(self, template_id: str) -> dict:
        """
        Lấy preview đầy đủ của template để review.
        
        Preview bao gồm:
        - OCR raw text của side1 và side2
        - Danh sách field đã map
        - Block chưa map (unmapped blocks)
        - Block có confidence thấp
        - Đường dẫn ảnh gốc
        
        Args:
            template_id: ID của template cần preview
            
        Returns:
            dict: Preview data với cấu trúc:
                {
                    "side1_raw_text": str,
                    "side2_raw_text": str,
                    "fields_by_side": {"side1": [...], "side2": [...]},
                    "unmapped_blocks": {"side1": [...], "side2": [...]},
                    "low_confidence_blocks": {"side1": [...], "side2": [...]},
                    "original_file_paths": {"side1": path, "side2": path}
                }
                
        Raises:
            LookupError: Nếu template không tồn tại
        """
        return self._svc.get_template_preview(template_id)

    def update_fields(self, template_id: str, patches: list, review_notes: str = "") -> dict:
        """
        Cập nhật danh sách field sau khi review.
        
        Người dùng có thể:
        - Thêm field mới
        - Sửa expected_value, compare_type, priority
        - Đánh dấu field là required/optional
        - Xóa field không cần thiết
        
        Args:
            template_id: ID của template cần update
            patches: List các TemplateFieldPatch, mỗi patch chứa:
                - side: "side1" hoặc "side2"
                - field_name: tên field (vd: "product_code")
                - expected_value: giá trị chuẩn
                - compare_type: "exact" | "regex" | "fuzzy" | "symbol_match"
                - priority: "critical" | "major" | "minor"
                - required: True/False
            review_notes: Ghi chú của reviewer (optional)
            
        Returns:
            dict: Template record đã update, status chuyển về REVIEW_REQUIRED
            
        Raises:
            LookupError: Nếu template không tồn tại
            ValueError: Nếu field data không hợp lệ
        """
        record = self._svc.update_fields(
            template_id=template_id,
            patches=patches,
            review_notes=review_notes,
        )
        return to_primitive(record)

    def approve(self, template_id: str, approved_by: str) -> dict:
        """
        Approve template — cho phép dùng trong runtime.
        
        Validation trước khi approve:
        - Template phải ở trạng thái REVIEW_REQUIRED
        - Phải có đủ field bắt buộc (vd: product_code cho side1)
        - Mọi field required phải có expected_value
        
        Sau khi approve:
        - Status chuyển thành APPROVED
        - Lưu approved_by và approved_at
        - Template sẵn sàng dùng cho runtime inspection
        
        Args:
            template_id: ID của template cần approve
            approved_by: Tên người approve (vd: "reviewer_01")
            
        Returns:
            dict: Template record với status = APPROVED
            
        Raises:
            LookupError: Nếu template không tồn tại
            ValueError: Nếu template chưa đủ điều kiện approve
        """
        record = self._svc.approve_template(template_id, approved_by)
        return to_primitive(record)

    def reject(self, template_id: str) -> dict:
        """
        Reject template — đánh dấu template không hợp lệ.
        
        Template bị reject sẽ:
        - Chuyển status thành REJECTED
        - Không thể dùng cho runtime
        - Có thể xóa hoặc giữ lại để tham khảo
        
        Args:
            template_id: ID của template cần reject
            
        Returns:
            dict: Template record với status = REJECTED
            
        Raises:
            LookupError: Nếu template không tồn tại
        """
        record = self._svc.reject_template(template_id)
        return to_primitive(record)
