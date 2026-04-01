from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "storage/app.db"


class AllocationRepository:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_table()

    # ---------------------------------------------------
    # TABLE SETUP (robust gegen beide Spalten)
    # ---------------------------------------------------

    def _ensure_table(self) -> None:
        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS allocation_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                weights TEXT,
                positions TEXT,
                signals TEXT,
                meta TEXT
            )
            """
        )

        conn.commit()
        conn.close()

    # ---------------------------------------------------
    # INSERT (immer neue Zeile)
    # ---------------------------------------------------

    def insert_snapshot(
        self,
        user_id: int,
        snapshot_date: str,
        weights: Dict[str, float],
        positions: List[Dict[str, Any]],
        signals: List[Dict[str, Any]],
        meta: Dict[str, Any],
    ) -> None:

        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            INSERT INTO allocation_snapshots (
                user_id,
                generated_at,
                snapshot_date,
                weights,
                positions,
                signals,
                meta
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                snapshot_date,  # 🔥 beide Felder gesetzt
                snapshot_date,
                json.dumps(weights),
                json.dumps(positions),
                json.dumps(signals),
                json.dumps(meta),
            ),
        )

        conn.commit()
        conn.close()

    # ---------------------------------------------------
    # READ ALL
    # ---------------------------------------------------

    def get_snapshots_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """
            SELECT user_id, snapshot_date, weights, positions, signals, meta
            FROM allocation_snapshots
            WHERE user_id = ?
            ORDER BY snapshot_date ASC
            """,
            (user_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        results = []

        for row in rows:
            results.append(
                {
                    "user_id": row[0],
                    "snapshot_date": row[1],
                    "weights": json.loads(row[2]) if row[2] else {},
                    "positions": json.loads(row[3]) if row[3] else [],
                    "signals": json.loads(row[4]) if row[4] else [],
                    "meta": json.loads(row[5]) if row[5] else {},
                }
            )

        return results

    # ---------------------------------------------------
    # READ LATEST
    # ---------------------------------------------------

    def get_latest_snapshot(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """
            SELECT user_id, snapshot_date, weights, positions, signals, meta
            FROM allocation_snapshots
            WHERE user_id = ?
            ORDER BY snapshot_date DESC
            LIMIT 1
            """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "user_id": row[0],
            "snapshot_date": row[1],
            "weights": json.loads(row[2]) if row[2] else {},
            "positions": json.loads(row[3]) if row[3] else [],
            "signals": json.loads(row[4]) if row[4] else [],
            "meta": json.loads(row[5]) if row[5] else {},
        }