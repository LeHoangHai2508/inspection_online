"""
Counter Service - Tổng hợp thống kê và KPI cho dashboard.

Service này cung cấp các chức năng:
1. Lấy KPI tổng hợp (total, OK, NG, UNCERTAIN, error_rate)
2. Lấy danh sách scan jobs gần đây

Kiến trúc:
    CounterService (business logic)
        ↓
    SQLiteCounterRepository (data access)
        ↓
    SQLite Database

Use cases:
    - Dashboard: Hiển thị KPI cards real-time
    - History table: Danh sách jobs gần đây
    - Monitoring: Theo dõi tỷ lệ lỗi
    - Reporting: Báo cáo tổng quan cho management

Design pattern:
    - Service layer: Chứa business logic (nếu cần)
    - Repository pattern: Tách biệt data access
    - Dependency injection: Service nhận repository qua constructor
"""
from __future__ import annotations

from src.db.repositories.counter_repo import SQLiteCounterRepository


class CounterService:
    """
    Service tổng hợp thống kê inspection cho dashboard.
    
    Service này là layer trung gian giữa API routes và repository.
    Hiện tại chủ yếu delegate sang repository, nhưng có thể mở rộng
    để thêm business logic như:
    - Caching: Cache KPI trong 5-10 giây
    - Filtering: Filter theo line_id, template_id, date_range
    - Aggregation: Tính toán thêm metrics phức tạp
    - Validation: Validate input params
    
    Attributes:
        _repository: SQLiteCounterRepository instance để query database
    """

    def __init__(self, repository: SQLiteCounterRepository) -> None:
        """
        Khởi tạo CounterService.
        
        Args:
            repository: SQLiteCounterRepository instance
        """
        self._repository = repository

    def get_summary(self) -> dict:
        """
        Lấy KPI tổng hợp cho dashboard.
        
        Trả về các chỉ số:
        - total: Tổng số scan jobs
        - ok: Số lượng PASS
        - ng: Số lượng FAIL
        - uncertain: Số lượng UNCERTAIN
        - error_rate_pct: Tỷ lệ lỗi (%)
        
        Returns:
            dict: KPI summary
                {
                    "total": 1000,
                    "ok": 850,
                    "ng": 120,
                    "uncertain": 30,
                    "error_rate_pct": 12.0
                }
        
        Examples:
            >>> service = CounterService(repository)
            >>> summary = service.get_summary()
            >>> print(summary["error_rate_pct"])
            12.0
        
        Notes:
            - Có thể thêm caching ở đây để giảm load database
            - Có thể thêm filter theo time range trong tương lai
        """
        return self._repository.get_summary()

    def get_recent_jobs(self, limit: int = 10) -> list[dict]:
        """
        Lấy danh sách scan jobs gần đây.
        
        Args:
            limit: Số lượng jobs tối đa (default: 10)
        
        Returns:
            list[dict]: Danh sách scan jobs, mỗi job là một dictionary
                [
                    {
                        "scan_job_id": "abc-123",
                        "template_id": "TPL_001",
                        "line_id": "line1",
                        "current_stage": "COMPLETED",
                        "created_at": "2024-01-15T10:30:00",
                        "overall_status": "OK",
                        "operator_action_required": false
                    },
                    ...
                ]
        
        Examples:
            >>> service = CounterService(repository)
            >>> jobs = service.get_recent_jobs(limit=5)
            >>> print(len(jobs))
            5
        
        Notes:
            - Kết quả sắp xếp theo created_at DESC (mới nhất trước)
            - Có thể thêm filter theo status, template_id trong tương lai
        """
        return self._repository.get_recent_jobs(limit=limit)
