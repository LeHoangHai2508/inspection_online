from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


class SQLiteIoTEventRepository:
    """Persists IoT publish attempts and their outcomes."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def log_publish(
        self,
        scan_job_id: str,
        action_type: str,
        publish_status: str,
        payload_path: str | None = None,
        retry_count: int = 0,
        last_error: str | None = None,
    ) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO iot_publish_logs (
                    scan_job_id, action_type, publish_status,
                    payload_path, retry_count, last_error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_job_id,
                    action_type,
                    publish_status,
                    payload_path,
                    retry_count,
                    last_error,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_by_job(self, scan_job_id: str) -> list[dict]:
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                """
                SELECT scan_job_id, action_type, publish_status,
                       payload_path, retry_count, last_error, created_at
                FROM iot_publish_logs
                WHERE scan_job_id = ?
                ORDER BY created_at DESC
                """,
                (scan_job_id,),
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        finally:
            conn.close()
