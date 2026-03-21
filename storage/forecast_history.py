import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("storage/forecast_history.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forecast_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        as_of TEXT,
        target TEXT,
        horizon_months INTEGER,
        forecast REAL,
        lower_bound REAL,
        upper_bound REAL,
        confidence_level REAL
    )
    """)

    conn.commit()
    conn.close()


def save_forecast(
    target: str,
    horizon_months: int,
    forecast: float,
    lower_bound: float,
    upper_bound: float,
    confidence_level: float,
    as_of: str
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO forecast_history (
        created_at,
        as_of,
        target,
        horizon_months,
        forecast,
        lower_bound,
        upper_bound,
        confidence_level
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        as_of,
        target,
        horizon_months,
        forecast,
        lower_bound,
        upper_bound,
        confidence_level
    ))

    conn.commit()
    conn.close()


def get_forecast_history(limit=50):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM forecast_history
    ORDER BY created_at DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return rows