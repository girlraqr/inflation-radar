from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from storage.database import get_connection


@dataclass
class PerformanceSnapshotRecord:
    user_id: int
    snapshot_date: str
    portfolio_value: float
    period_return: float
    cumulative_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    hit_rate: float
    intelligence: dict[str, Any]


class PortfolioPerformanceRepository:
    def __init__(self) -> None:
        self._connection_factory = get_connection

    # =========================
    # WRITE
    # =========================

    def upsert_snapshot(self, record: PerformanceSnapshotRecord) -> None:
        with self._connection_factory() as conn:
            conn.execute(
                """
                INSERT INTO portfolio_performance_snapshots (
                    user_id,
                    snapshot_date,
                    portfolio_value,
                    period_return,
                    cumulative_return,
                    annualized_return,
                    annualized_volatility,
                    sharpe_ratio,
                    max_drawdown,
                    hit_rate,
                    intelligence_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, snapshot_date)
                DO UPDATE SET
                    portfolio_value = excluded.portfolio_value,
                    period_return = excluded.period_return,
                    cumulative_return = excluded.cumulative_return,
                    annualized_return = excluded.annualized_return,
                    annualized_volatility = excluded.annualized_volatility,
                    sharpe_ratio = excluded.sharpe_ratio,
                    max_drawdown = excluded.max_drawdown,
                    hit_rate = excluded.hit_rate,
                    intelligence_json = excluded.intelligence_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    record.user_id,
                    record.snapshot_date,
                    record.portfolio_value,
                    record.period_return,
                    record.cumulative_return,
                    record.annualized_return,
                    record.annualized_volatility,
                    record.sharpe_ratio,
                    record.max_drawdown,
                    record.hit_rate,
                    json.dumps(record.intelligence),
                ),
            )
            conn.commit()

    # =========================
    # READ
    # =========================

    def get_history(
        self,
        user_id: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._connection_factory() as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT *
                FROM portfolio_performance_snapshots
                WHERE user_id = ?
                ORDER BY snapshot_date DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

            results: list[dict[str, Any]] = []

            for row in rows:
                payload = dict(row)
                payload["intelligence"] = json.loads(payload.get("intelligence_json") or "{}")
                payload.pop("intelligence_json", None)
                results.append(payload)

            return results

    def get_latest(self, user_id: int) -> dict[str, Any] | None:
        rows = self.get_history(user_id=user_id, limit=1)
        return rows[0] if rows else None

    def get_latest_summary_payload(self, user_id: int) -> dict[str, Any] | None:
        latest = self.get_latest(user_id=user_id)
        if latest is None:
            return None

        intelligence = latest.get("intelligence") or {}

        payload = {
            "summary": {
                "observations": 1,
                "total_return": float(latest.get("cumulative_return", 0.0)),
                "annualized_return": float(latest.get("annualized_return", 0.0)),
                "volatility": float(latest.get("annualized_volatility", 0.0)),
                "sharpe_ratio": float(latest.get("sharpe_ratio", 0.0)),
                "max_drawdown": float(latest.get("max_drawdown", 0.0)),
                "latest_value": float(latest.get("portfolio_value", 0.0)),
                "latest_period_return": float(latest.get("period_return", 0.0)),
                "latest_cumulative_return": float(latest.get("cumulative_return", 0.0)),
            },
            "signal_accuracy": {
                "overall_hit_rate": float(latest.get("hit_rate", 0.0)),
                "total_signals": 0,
                "hits": 0,
                "by_signal": {},
            },
            "intelligence": {
                "recent_3m_momentum": float(intelligence.get("recent_3m_momentum", 0.0)),
                "current_drawdown": float(intelligence.get("current_drawdown", 0.0)),
                "signal_backing_strength": float(intelligence.get("signal_backing_strength", 0.0)),
                "narratives": intelligence.get("narratives", []),
            },
            "meta": {
                "source": "db",
                "snapshot_date": latest.get("snapshot_date"),
            },
        }

        return payload