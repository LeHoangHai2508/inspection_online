from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "sqlite" / "inspection.db"
SCHEMA_PATH = ROOT / "src" / "db" / "schema.sql"


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()

    print(f"Created SQLite DB at: {DB_PATH}")


if __name__ == "__main__":
    main()