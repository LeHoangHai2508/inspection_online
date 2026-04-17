from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def elapsed_ms(started_at: datetime) -> int:
    delta = utc_now() - started_at
    return int(delta.total_seconds() * 1000)
