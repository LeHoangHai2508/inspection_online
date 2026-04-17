from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class SQLiteCounterRepository:
    """Reads aggregated inspection counts from the DB."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_summary(self) -> dict:
        """Return total / OK / NG / UNCERTAIN counts from overall_results."""
        conn = sqlite3.connect(self._db_path)
        try:
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
            total, ok_count, ng_count, uncertain_count = row
            total = total or 0
            ok_count = ok_count or 0
            ng_count = ng_count or 0
            uncertain_count = uncertain_count or 0
            error_rate = round((ng_count / total) * 100, 2) if total else 0.0
            return {
                "total": total,
                "ok": ok_count,
                "ng": ng_count,
                "uncertain": uncertain_count,
                "error_rate_pct": error_rate,
            }
        finally:
            conn.close()

    def get_recent_jobs(self, limit: int = 10) -> list[dict]:
        """Return the most recent scan jobs with their overall status."""
        conn = sqlite3.connect(self._db_path)
        try:
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
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        finally:
            conn.close()
