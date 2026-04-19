"""
Counter Repository - Data access layer cho thống kê và KPI.

Repository này chịu trách nhiệm:
1. Query KPI tổng hợp từ bảng overall_results
2. Query danh sách scan jobs gần đây từ bảng scan_jobs

Database schema:
    overall_results:
        - scan_job_id (PK)
        - overall_status: OK/NG/UNCERTAIN
        - operator_action_required: boolean
        - created_at: timestamp
    
    scan_jobs:
        - scan_job_id (PK)
        - template_id: FK to templates
        - line_id: Production line ID
        - current_stage: PENDING/SIDE1/SIDE2/COMPLETED
        - created_at: timestamp

Design pattern:
    - Repository pattern: Tách biệt data access khỏi business logic
    - Raw SQL: Dùng sqlite3 trực tiếp cho performance
    - Connection management: Open/close connection mỗi query
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class SQLiteCounterRepository:
    """
    Repository để query thống kê inspection từ SQLite.
    
    Class này cung cấp các methods để:
    1. Tính toán KPI tổng hợp (total, OK, NG, error_rate)
    2. Lấy danh sách scan jobs gần đây
    
    Attributes:
        _db_path: Đường dẫn đến SQLite database file
    """

    def __init__(self, db_path: str) -> None:
        """
        Khởi tạo repository.
        
        Args:
            db_path: Đường dẫn tuyệt đối đến SQLite database
                    VD: "/path/to/inspection.db"
        """
        self._db_path = db_path

    def get_summary(self) -> dict:
        """
        Tính toán KPI tổng hợp từ bảng overall_results.
        
        Query này đếm số lượng scan jobs theo từng status:
        - total: Tổng số jobs
        - ok: Số jobs có overall_status = 'OK'
        - ng: Số jobs có overall_status = 'NG'
        - uncertain: Số jobs có overall_status = 'UNCERTAIN'
        - error_rate_pct: Tỷ lệ lỗi = (ng / total) * 100
        
        SQL logic:
            - COUNT(*): Đếm tổng số rows
            - SUM(CASE WHEN ...): Đếm có điều kiện
            - Tính error_rate từ ng_count / total
        
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
            >>> repo = SQLiteCounterRepository("inspection.db")
            >>> summary = repo.get_summary()
            >>> print(f"Error rate: {summary['error_rate_pct']}%")
            Error rate: 12.0%
        
        Notes:
            - Nếu database rỗng, trả về all zeros
            - error_rate_pct được round đến 2 chữ số thập phân
            - Connection được close trong finally block để đảm bảo cleanup
        """
        conn = sqlite3.connect(self._db_path)
        try:
            # Query đếm số lượng theo từng status
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN overall_status = 'OK' THEN 1 ELSE 0 END) AS ok_count,
                    SUM(CASE WHEN overall_status = 'NG' THEN 1 ELSE 0 END) AS ng_count,
                    SUM(CASE WHEN overall_status = 'UNCERTAIN' THEN 1 ELSE 0 END) AS uncertain_count
                FROM overall_results
                """
            ).fetchone()
            
            # Unpack kết quả và handle NULL (database rỗng)
            total, ok_count, ng_count, uncertain_count = row
            total = total or 0
            ok_count = ok_count or 0
            ng_count = ng_count or 0
            uncertain_count = uncertain_count or 0
            
            # Tính error rate (%), tránh chia cho 0
            error_rate = round((ng_count / total) * 100, 2) if total else 0.0
            
            return {
                "total": total,
                "ok": ok_count,
                "ng": ng_count,
                "uncertain": uncertain_count,
                "error_rate_pct": error_rate,
            }
        finally:
            # Đảm bảo connection được close dù có exception hay không
            conn.close()

    def get_recent_jobs(self, limit: int = 10) -> list[dict]:
        """
        Lấy danh sách scan jobs gần đây nhất.
        
        Query này JOIN giữa scan_jobs và overall_results để lấy:
        - Thông tin job: scan_job_id, template_id, line_id, current_stage
        - Thông tin kết quả: overall_status, operator_action_required
        - Timestamp: created_at
        
        Kết quả được sắp xếp theo created_at DESC (mới nhất trước).
        
        SQL logic:
            - LEFT JOIN: Giữ lại jobs chưa có kết quả (overall_results NULL)
            - ORDER BY created_at DESC: Mới nhất trước
            - LIMIT: Giới hạn số lượng rows
        
        Args:
            limit: Số lượng jobs tối đa (default: 10)
        
        Returns:
            list[dict]: Danh sách scan jobs
                [
                    {
                        "scan_job_id": "abc-123",
                        "template_id": "TPL_001",
                        "line_id": "line1",
                        "current_stage": "COMPLETED",
                        "created_at": "2024-01-15T10:30:00",
                        "overall_status": "OK",
                        "operator_action_required": 0
                    },
                    ...
                ]
        
        Examples:
            >>> repo = SQLiteCounterRepository("inspection.db")
            >>> jobs = repo.get_recent_jobs(limit=5)
            >>> for job in jobs:
            ...     print(f"{job['scan_job_id']}: {job['overall_status']}")
            abc-123: OK
            abc-124: NG
            abc-125: UNCERTAIN
        
        Notes:
            - LEFT JOIN đảm bảo jobs chưa hoàn thành vẫn được trả về
            - overall_status và operator_action_required có thể NULL
            - Có thể thêm filter WHERE clause trong tương lai:
              * WHERE overall_status = 'NG'
              * WHERE template_id = 'TPL_001'
              * WHERE created_at > '2024-01-01'
        """
        conn = sqlite3.connect(self._db_path)
        try:
            # Query JOIN scan_jobs với overall_results
            cursor = conn.execute(
                """
                SELECT sj.scan_job_id, sj.template_id, sj.line_id,
                       sj.current_stage, sj.created_at,
                       ov.overall_status, ov.operator_action_required
                FROM scan_jobs sj
                LEFT JOIN overall_results ov ON sj.scan_job_id = ov.scan_job_id
                ORDER BY sj.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            
            # Convert rows sang list of dicts
            # Lấy tên columns từ cursor.description
            cols = [d[0] for d in cursor.description]
            
            # Zip column names với values để tạo dict
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        finally:
            # Đảm bảo connection được close
            conn.close()
