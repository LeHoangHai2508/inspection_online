from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum


def to_primitive(value):
    if is_dataclass(value):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_primitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_primitive(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value
