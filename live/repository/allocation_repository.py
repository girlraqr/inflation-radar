from __future__ import annotations

import json
import sqlite3
from typing import Any

from storage.database import get_connection


class AllocationRepository:
    def __init__(self) -> None:
        self._connection_factory = get_connection

    # =========================
    # WRITE
    # =========================

    def upsert_snapshot(
        self,
        user_id: int,
        snapshot_date: str,
        generated_at: str,
        rebalance_required: int,
        rebalance_reason: str,
        total_invested_weight: float,
        cash_weight: float,
        allocation_hint: str,
        weights: str,
        positions: str,
        signals: str,
        meta: str,
    ) -> None:

        with self._connection_factory() as conn:
            conn.execute(
                """
                INSERT INTO allocation_snapshots (
                    user_id,
                    snapshot_date,
                    generated_at,
                    rebalance_required,
                    rebalance_reason,
                    total_invested_weight,
                    cash_weight,
                    allocation_hint,
                    weights,
                    positions,
                    signals,
                    meta
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, snapshot_date)
                DO UPDATE SET
                    generated_at = excluded.generated_at,
                    rebalance_required = excluded.rebalance_required,
                    rebalance_reason = excluded.rebalance_reason,
                    total_invested_weight = excluded.total_invested_weight,
                    cash_weight = excluded.cash_weight,
                    allocation_hint = excluded.allocation_hint,
                    weights = excluded.weights,
                    positions = excluded.positions,
                    signals = excluded.signals,
                    meta = excluded.meta
                """,
                (
                    user_id,
                    snapshot_date,
                    generated_at,
                    rebalance_required,
                    rebalance_reason,
                    total_invested_weight,
                    cash_weight,
                    allocation_hint,
                    weights,
                    positions,
                    signals,
                    meta,
                ),
            )
            conn.commit()

    # =========================
    # READ
    # =========================

    def get_user_snapshots(
        self,
        user_id: int,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:

        with self._connection_factory() as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT *
                FROM allocation_snapshots
                WHERE user_id = ?
                ORDER BY snapshot_date ASC
            """

            params: list[Any] = [user_id]

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()

            results: list[dict[str, Any]] = []

            for row in rows:
                record = dict(row)

                record["weights"] = self._safe_json_load(record.get("weights"))
                record["positions"] = self._safe_json_load(record.get("positions"))
                record["signals"] = self._safe_json_load(record.get("signals"))
                record["meta"] = self._safe_json_load(record.get("meta"))

                results.append(record)

            return results

    def get_latest_snapshot(self, user_id: int) -> dict[str, Any] | None:
        snapshots = self.get_user_snapshots(user_id=user_id, limit=1)
        return snapshots[-1] if snapshots else None

    # =========================
    # HELPERS
    # =========================

    def _safe_json_load(self, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, (dict, list)):
            return value

        try:
            return json.loads(value)
        except Exception:
            return value