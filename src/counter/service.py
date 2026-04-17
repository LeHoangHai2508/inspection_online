from __future__ import annotations

from src.db.repositories.counter_repo import SQLiteCounterRepository


class CounterService:
    """Aggregates inspection statistics for the dashboard."""

    def __init__(self, repository: SQLiteCounterRepository) -> None:
        self._repository = repository

    def get_summary(self) -> dict:
        return self._repository.get_summary()

    def get_recent_jobs(self, limit: int = 10) -> list[dict]:
        return self._repository.get_recent_jobs(limit=limit)
