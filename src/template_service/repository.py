from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Protocol

from src.domain.enums import TemplateStatus
from src.domain.models import TemplateRecord


class TemplateRepository(Protocol):
    def save(self, record: TemplateRecord) -> TemplateRecord:
        ...

    def get_latest(self, template_id: str) -> TemplateRecord | None:
        ...

    def get_approved(self, template_id: str) -> TemplateRecord | None:
        ...

    def next_version(self, template_id: str) -> str:
        ...


class InMemoryTemplateRepository:
    """Simple repository used now and easy to swap for SQLite later."""

    def __init__(self) -> None:
        self._records: dict[str, list[TemplateRecord]] = defaultdict(list)

    def save(self, record: TemplateRecord) -> TemplateRecord:
        records = self._records[record.template_id]

        for index, existing in enumerate(records):
            if existing.template_version == record.template_version:
                records[index] = deepcopy(record)
                return deepcopy(record)

        records.append(deepcopy(record))
        return deepcopy(record)

    def get_latest(self, template_id: str) -> TemplateRecord | None:
        records = self._records.get(template_id, [])
        if not records:
            return None
        return deepcopy(records[-1])

    def get_approved(self, template_id: str) -> TemplateRecord | None:
        records = self._records.get(template_id, [])
        approved_records = [
            record for record in records if record.status == TemplateStatus.APPROVED
        ]
        if not approved_records:
            return None
        return deepcopy(approved_records[-1])

    def next_version(self, template_id: str) -> str:
        current_version = len(self._records.get(template_id, [])) + 1
        return f"v{current_version}"
