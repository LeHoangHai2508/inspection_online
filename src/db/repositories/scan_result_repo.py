from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from src.domain.models import OverallInspectionResult, SideInspectionResult


class SQLiteScanResultRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def start_job(
        self,
        scan_job_id: str,
        template_id: str,
        current_stage: str,
        line_id: str,
        station_id: str,
    ) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute(
                """
                INSERT OR REPLACE INTO scan_jobs (
                    scan_job_id, template_id, current_stage, line_id, station_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_job_id,
                    template_id,
                    current_stage,
                    line_id,
                    station_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def update_stage(self, scan_job_id: str, current_stage: str) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute(
                "UPDATE scan_jobs SET current_stage = ? WHERE scan_job_id = ?",
                (current_stage, scan_job_id),
            )
            connection.commit()
        finally:
            connection.close()

    def save_side_result(self, scan_job_id: str, result: SideInspectionResult) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute(
                """
                INSERT INTO side_results (
                    scan_job_id, side, status, raw_text, processing_time_ms, annotated_assets_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_job_id,
                    result.side.value,
                    result.status.value,
                    result.raw_text,
                    result.processing_time_ms,
                    json.dumps(result.annotated_assets, ensure_ascii=False),
                ),
            )

            for error in result.errors:
                connection.execute(
                    """
                    INSERT INTO compare_results (
                        scan_job_id, side, field_name, error_type, severity,
                        expected_value, actual_value, confidence, bbox_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scan_job_id,
                        error.side.value,
                        error.field_name,
                        error.error_type.value,
                        error.severity.value,
                        error.expected_value,
                        error.actual_value,
                        error.confidence,
                        json.dumps(
                            [
                                error.bbox.x1,
                                error.bbox.y1,
                                error.bbox.x2,
                                error.bbox.y2,
                            ]
                        )
                        if error.bbox
                        else None,
                    ),
                )

            connection.commit()
        finally:
            connection.close()

    def save_overall_result(self, result: OverallInspectionResult) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute(
                """
                INSERT OR REPLACE INTO overall_results (
                    scan_job_id, side1_status, side2_status, overall_status,
                    operator_action_required, highest_severity, publish_to_iot
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.scan_job_id,
                    result.side1_result.status.value if result.side1_result else None,
                    result.side2_result.status.value if result.side2_result else None,
                    result.overall_status.value if result.overall_status else None,
                    (
                        result.operator_action_required.value
                        if result.operator_action_required
                        else None
                    ),
                    result.highest_severity.value if result.highest_severity else None,
                    int(result.publish_to_iot),
                ),
            )
            connection.commit()
        finally:
            connection.close()
