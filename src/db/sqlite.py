from __future__ import annotations

import sqlite3
from pathlib import Path


def initialize_database(db_path: str, schema_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = Path(schema_path).read_text(encoding="utf-8")

    connection = sqlite3.connect(path)
    try:
        connection.executescript(schema)
        connection.commit()
    finally:
        connection.close()
