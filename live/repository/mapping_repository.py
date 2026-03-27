from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional


class MappingRepository:

    def __init__(self, db_path: str = "storage/app.db"):
        self.db_path = db_path

    # =========================================================
    # READ (für Mapping Engine)
    # =========================================================

    def get_mapping(self, signal: str, regime: str) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT theme, theme_weight, asset, asset_weight
                FROM signal_asset_mapping
                WHERE signal = ?
                  AND regime = ?
                  AND is_active = 1
                ORDER BY id ASC
                """,
                (signal, regime),
            )

            rows = cur.fetchall()

            return [
                {
                    "theme": r["theme"],
                    "theme_weight": float(r["theme_weight"]),
                    "asset": r["asset"],
                    "asset_weight": float(r["asset_weight"]),
                }
                for r in rows
            ]
        finally:
            conn.close()

    # =========================================================
    # CREATE
    # =========================================================

    def create_mapping(self, data: Dict) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO signal_asset_mapping
                (signal, regime, theme, theme_weight, asset, asset_weight)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data["signal"],
                    data["regime"],
                    data["theme"],
                    float(data["theme_weight"]),
                    data["asset"],
                    float(data["asset_weight"]),
                ),
            )

            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def create_many(self, rows: List[Dict]) -> List[int]:
        if not rows:
            return []

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            inserted_ids: List[int] = []

            for row in rows:
                cur.execute(
                    """
                    INSERT INTO signal_asset_mapping
                    (signal, regime, theme, theme_weight, asset, asset_weight)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["signal"],
                        row["regime"],
                        row["theme"],
                        float(row["theme_weight"]),
                        row["asset"],
                        float(row["asset_weight"]),
                    ),
                )
                inserted_ids.append(cur.lastrowid)

            conn.commit()
            return inserted_ids
        finally:
            conn.close()

    # =========================================================
    # READ ALL (für API)
    # =========================================================

    def get_all(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT id, signal, regime, theme, theme_weight,
                       asset, asset_weight, is_active, created_at
                FROM signal_asset_mapping
                ORDER BY id DESC
                """
            )

            rows = cur.fetchall()

            return [
                {
                    "id": r["id"],
                    "signal": r["signal"],
                    "regime": r["regime"],
                    "theme": r["theme"],
                    "theme_weight": float(r["theme_weight"]),
                    "asset": r["asset"],
                    "asset_weight": float(r["asset_weight"]),
                    "is_active": int(r["is_active"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_group(self, signal: str, regime: str, active_only: bool = False) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()

            query = """
                SELECT id, signal, regime, theme, theme_weight,
                       asset, asset_weight, is_active, created_at
                FROM signal_asset_mapping
                WHERE signal = ?
                  AND regime = ?
            """
            params: List[object] = [signal, regime]

            if active_only:
                query += " AND is_active = 1"

            query += " ORDER BY theme ASC, id ASC"

            cur.execute(query, params)
            rows = cur.fetchall()

            return [
                {
                    "id": r["id"],
                    "signal": r["signal"],
                    "regime": r["regime"],
                    "theme": r["theme"],
                    "theme_weight": float(r["theme_weight"]),
                    "asset": r["asset"],
                    "asset_weight": float(r["asset_weight"]),
                    "is_active": int(r["is_active"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        finally:
            conn.close()

    # =========================================================
    # UPDATE
    # =========================================================

    def update_mapping(self, mapping_id: int, data: Dict) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            updates = []
            values = []

            if data.get("theme_weight") is not None:
                updates.append("theme_weight = ?")
                values.append(float(data["theme_weight"]))

            if data.get("asset_weight") is not None:
                updates.append("asset_weight = ?")
                values.append(float(data["asset_weight"]))

            if data.get("is_active") is not None:
                updates.append("is_active = ?")
                values.append(int(data["is_active"]))

            if not updates:
                return False

            values.append(mapping_id)

            query = f"""
                UPDATE signal_asset_mapping
                SET {', '.join(updates)}
                WHERE id = ?
            """

            cur.execute(query, values)
            conn.commit()

            return cur.rowcount > 0
        finally:
            conn.close()

    def deactivate_group(self, signal: str, regime: str) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE signal_asset_mapping
                SET is_active = 0
                WHERE signal = ?
                  AND regime = ?
                  AND is_active = 1
                """,
                (signal, regime),
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    # =========================================================
    # DELETE
    # =========================================================

    def delete_mapping(self, mapping_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            cur.execute(
                "DELETE FROM signal_asset_mapping WHERE id = ?",
                (mapping_id,),
            )

            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # =========================================================
    # OPTIONAL: GET SINGLE
    # =========================================================

    def get_by_id(self, mapping_id: int) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT id, signal, regime, theme, theme_weight,
                       asset, asset_weight, is_active, created_at
                FROM signal_asset_mapping
                WHERE id = ?
                """,
                (mapping_id,),
            )

            row = cur.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "signal": row["signal"],
                "regime": row["regime"],
                "theme": row["theme"],
                "theme_weight": float(row["theme_weight"]),
                "asset": row["asset"],
                "asset_weight": float(row["asset_weight"]),
                "is_active": int(row["is_active"]),
                "created_at": row["created_at"],
            }
        finally:
            conn.close()