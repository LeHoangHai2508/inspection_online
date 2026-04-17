from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from src.domain.enums import CompareType, FieldPriority, InspectionSide, TemplateStatus
from src.domain.models import (
    BoundingBox,
    OCRBlock,
    StoredFile,
    TemplateFieldDefinition,
    TemplateRecord,
    TemplateSideDefinition,
)


class SQLiteTemplateRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def save(self, record: TemplateRecord) -> TemplateRecord:
        connection = sqlite3.connect(self._db_path)
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO templates (
                    template_id, template_name, product_code, status, created_by, created_at, review_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    template_name=excluded.template_name,
                    product_code=excluded.product_code,
                    status=excluded.status,
                    review_notes=excluded.review_notes
                """,
                (
                    record.template_id,
                    record.template_name,
                    record.product_code,
                    record.status.value,
                    record.created_by,
                    record.created_at.isoformat(),
                    record.review_notes,
                ),
            )

            cursor.execute(
                "DELETE FROM template_versions WHERE template_id = ? AND version = ?",
                (record.template_id, record.template_version),
            )
            cursor.execute(
                "DELETE FROM template_fields WHERE template_id = ? AND version = ?",
                (record.template_id, record.template_version),
            )
            cursor.execute(
                "DELETE FROM template_blocks WHERE template_id = ? AND version = ?",
                (record.template_id, record.template_version),
            )

            for side in (InspectionSide.SIDE1, InspectionSide.SIDE2):
                side_definition = record.get_side(side)
                cursor.execute(
                    """
                    INSERT INTO template_versions (
                        template_id, version, side, raw_text, source_file_path, approved_by, approved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.template_id,
                        record.template_version,
                        side.value,
                        side_definition.raw_text,
                        side_definition.source_file.storage_path
                        if side_definition.source_file
                        else None,
                        record.approved_by,
                        record.approved_at.isoformat() if record.approved_at else None,
                    ),
                )

                for field in side_definition.fields:
                    cursor.execute(
                        """
                        INSERT INTO template_fields (
                            template_id, version, side, field_name, field_type, required,
                            compare_type, priority, expected_value, bbox_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.template_id,
                            record.template_version,
                            side.value,
                            field.field_name,
                            field.field_type,
                            int(field.required),
                            field.compare_type.value,
                            field.priority.value,
                            field.expected_value,
                            _bbox_to_json(field.bbox),
                        ),
                    )

                for block in side_definition.ocr_blocks:
                    cursor.execute(
                        """
                        INSERT INTO template_blocks (
                            template_id, version, side, line_index, text, confidence, bbox_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.template_id,
                            record.template_version,
                            side.value,
                            block.line_index,
                            block.text,
                            block.confidence,
                            _bbox_to_json(block.bbox),
                        ),
                    )

            connection.commit()
            return record
        finally:
            connection.close()

    def get_latest(self, template_id: str) -> TemplateRecord | None:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            template_row = connection.execute(
                "SELECT * FROM templates WHERE template_id = ?",
                (template_id,),
            ).fetchone()
            if template_row is None:
                return None

            version_rows = connection.execute(
                """
                SELECT * FROM template_versions
                WHERE template_id = ?
                ORDER BY id DESC
                """,
                (template_id,),
            ).fetchall()
            if not version_rows:
                return None

            latest_version = version_rows[0]["version"]
            return self._build_record(connection, template_row, latest_version)
        finally:
            connection.close()

    def get_approved(self, template_id: str) -> TemplateRecord | None:
        record = self.get_latest(template_id)
        if record is None or record.status != TemplateStatus.APPROVED:
            return None
        return record

    def next_version(self, template_id: str) -> str:
        connection = sqlite3.connect(self._db_path)
        try:
            row = connection.execute(
                "SELECT COUNT(*) FROM template_versions WHERE template_id = ?",
                (template_id,),
            ).fetchone()
            version_number = 1 if row is None else int(row[0] / 2) + 1
            return f"v{version_number}"
        finally:
            connection.close()

    def _build_record(
        self,
        connection: sqlite3.Connection,
        template_row,
        version: str,
    ) -> TemplateRecord:
        sides = {}
        for side in (InspectionSide.SIDE1, InspectionSide.SIDE2):
            version_row = connection.execute(
                """
                SELECT * FROM template_versions
                WHERE template_id = ? AND version = ? AND side = ?
                ORDER BY id DESC LIMIT 1
                """,
                (template_row["template_id"], version, side.value),
            ).fetchone()
            field_rows = connection.execute(
                """
                SELECT * FROM template_fields
                WHERE template_id = ? AND version = ? AND side = ?
                """,
                (template_row["template_id"], version, side.value),
            ).fetchall()
            block_rows = connection.execute(
                """
                SELECT * FROM template_blocks
                WHERE template_id = ? AND version = ? AND side = ?
                ORDER BY line_index
                """,
                (template_row["template_id"], version, side.value),
            ).fetchall()

            sides[side] = TemplateSideDefinition(
                side=side,
                raw_text=version_row["raw_text"] if version_row else "",
                fields=[
                    TemplateFieldDefinition(
                        field_name=row["field_name"],
                        expected_value=row["expected_value"] or "",
                        side=side,
                        field_type=row["field_type"],
                        required=bool(row["required"]),
                        compare_type=CompareType(row["compare_type"]),
                        priority=FieldPriority(row["priority"]),
                        bbox=_json_to_bbox(row["bbox_json"]),
                    )
                    for row in field_rows
                ],
                ocr_blocks=[
                    OCRBlock(
                        text=row["text"],
                        bbox=_json_to_bbox(row["bbox_json"]) or BoundingBox(0, 0, 0, 0),
                        confidence=row["confidence"] or 0.0,
                        line_index=row["line_index"],
                    )
                    for row in block_rows
                ],
                source_file=(
                    StoredFile(
                        filename="stored_asset",
                        storage_path=version_row["source_file_path"],
                    )
                    if version_row and version_row["source_file_path"]
                    else None
                ),
            )

        return TemplateRecord(
            template_id=template_row["template_id"],
            template_version=version,
            template_name=template_row["template_name"],
            product_code=template_row["product_code"],
            created_by=template_row["created_by"],
            status=TemplateStatus(template_row["status"]),
            sides=sides,
            approved_by=(
                connection.execute(
                    """
                    SELECT approved_by FROM template_versions
                    WHERE template_id = ? AND version = ? AND approved_by IS NOT NULL
                    ORDER BY id DESC LIMIT 1
                    """,
                    (template_row["template_id"], version),
                ).fetchone() or {"approved_by": None}
            )["approved_by"],
            created_at=datetime.fromisoformat(template_row["created_at"]),
            review_notes=template_row["review_notes"] or "",
        )


def _bbox_to_json(bbox: BoundingBox | None) -> str | None:
    if bbox is None:
        return None
    return json.dumps([bbox.x1, bbox.y1, bbox.x2, bbox.y2])


def _json_to_bbox(value: str | None) -> BoundingBox | None:
    if not value:
        return None
    x1, y1, x2, y2 = json.loads(value)
    return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
