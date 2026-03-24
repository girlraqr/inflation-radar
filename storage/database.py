from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import settings


DB_PATH = Path(settings.database_path)
MIGRATIONS_PATH = Path("storage/migrations")


def ensure_database_directory() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    ensure_database_directory()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database() -> None:
    ensure_database_directory()

    if not MIGRATIONS_PATH.exists():
        return

    migration_files = sorted(MIGRATIONS_PATH.glob("*.sql"))
    with get_connection() as connection:
        for migration_file in migration_files:
            sql = migration_file.read_text(encoding="utf-8").strip()
            if sql:
                connection.executescript(sql)