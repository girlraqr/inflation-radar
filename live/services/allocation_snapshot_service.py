from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from live.repository.allocation_repository import AllocationRepository
from services.portfolio_performance_adapter import PortfolioPerformanceAdapter


logger = logging.getLogger(__name__)


@dataclass
class AllocationSnapshotResult:
    success: bool
    persisted: bool
    performance_updated: bool
    snapshot_payload: dict[str, Any]


class AllocationSnapshotService:
    """
    Persists portfolio allocation snapshots and triggers performance updates.

    Responsibilities:
    - normalize portfolio payloads
    - persist allocation snapshots
    - trigger performance recalculation after snapshot persistence
    - never let performance update failures block snapshot persistence
    """

    def __init__(
        self,
        allocation_repository: AllocationRepository | None = None,
        performance_adapter: PortfolioPerformanceAdapter | None = None,
    ) -> None:
        self.allocation_repository = allocation_repository or AllocationRepository()
        self.performance_adapter = performance_adapter or PortfolioPerformanceAdapter()

    def persist_snapshot(
        self,
        user_id: int,
        portfolio: dict[str, Any],
        snapshot_date: str | None = None,
    ) -> AllocationSnapshotResult:
        """
        Persist a portfolio allocation snapshot and trigger performance update.

        Args:
            user_id: authenticated user id
            portfolio: portfolio payload from PortfolioEngineService.build_portfolio(...)
            snapshot_date: optional YYYY-MM-DD string; defaults to generated_at/current UTC date

        Returns:
            AllocationSnapshotResult
        """
        if not isinstance(portfolio, dict):
            raise ValueError("portfolio must be a dict")

        payload = self._build_snapshot_payload(
            user_id=user_id,
            portfolio=portfolio,
            snapshot_date=snapshot_date,
        )

        self._persist_payload(payload)

        performance_updated = self._trigger_performance_update(user_id=user_id)

        return AllocationSnapshotResult(
            success=True,
            persisted=True,
            performance_updated=performance_updated,
            snapshot_payload=payload,
        )

    def persist_from_portfolio(
        self,
        user_id: int,
        portfolio: dict[str, Any],
        snapshot_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Convenience wrapper that returns a plain dict instead of a dataclass.
        Useful if existing callers already expect dict-like service responses.
        """
        result = self.persist_snapshot(
            user_id=user_id,
            portfolio=portfolio,
            snapshot_date=snapshot_date,
        )
        return {
            "success": result.success,
            "persisted": result.persisted,
            "performance_updated": result.performance_updated,
            "snapshot_payload": result.snapshot_payload,
        }

    def _build_snapshot_payload(
        self,
        user_id: int,
        portfolio: dict[str, Any],
        snapshot_date: str | None = None,
    ) -> dict[str, Any]:
        generated_at = portfolio.get("generated_at") or self._utc_now_iso()
        resolved_snapshot_date = snapshot_date or self._extract_snapshot_date(generated_at)

        positions = portfolio.get("positions") or []
        meta = portfolio.get("meta") or {}

        weights = self._extract_weights_from_positions(positions)
        signals = self._extract_signals_from_positions(positions)

        payload: dict[str, Any] = {
            "user_id": int(user_id),
            "snapshot_date": resolved_snapshot_date,
            "generated_at": generated_at,
            "rebalance_required": bool(portfolio.get("rebalance_required", False)),
            "rebalance_reason": str(portfolio.get("rebalance_reason", "")),
            "total_invested_weight": float(portfolio.get("total_invested_weight", 0.0)),
            "cash_weight": float(portfolio.get("cash_weight", 0.0)),
            "allocation_hint": str(portfolio.get("allocation_hint", "")),
            "weights": weights,
            "positions": positions,
            "signals": signals,
            "meta": meta,
        }

        return payload

    def _persist_payload(self, payload: dict[str, Any]) -> None:
        """
        Tries multiple repository method names for compatibility with your codebase.
        """
        serialized_payload = self._serialize_payload_for_storage(payload)

        candidate_methods = [
            "upsert_snapshot",
            "create_snapshot",
            "save_snapshot",
            "insert_snapshot",
        ]

        for method_name in candidate_methods:
            repo_method = getattr(self.allocation_repository, method_name, None)
            if callable(repo_method):
                try:
                    repo_method(**serialized_payload)
                    logger.info(
                        "Allocation snapshot persisted via %s for user_id=%s snapshot_date=%s",
                        method_name,
                        serialized_payload["user_id"],
                        serialized_payload["snapshot_date"],
                    )
                    return
                except TypeError:
                    # repository method may accept a single payload dict instead of kwargs
                    repo_method(serialized_payload)
                    logger.info(
                        "Allocation snapshot persisted via %s(payload) for user_id=%s snapshot_date=%s",
                        method_name,
                        serialized_payload["user_id"],
                        serialized_payload["snapshot_date"],
                    )
                    return

        raise AttributeError(
            "AllocationRepository does not expose a supported snapshot persistence method. "
            "Expected one of: upsert_snapshot, create_snapshot, save_snapshot, insert_snapshot."
        )

    def _trigger_performance_update(self, user_id: int) -> bool:
        """
        Performance update must never block snapshot persistence.
        """
        try:
            self.performance_adapter.get_performance_for_user(user_id=user_id)
            logger.info("Performance update completed for user_id=%s", user_id)
            return True
        except Exception as exc:
            logger.warning(
                "Performance update failed for user_id=%s: %s",
                user_id,
                str(exc),
                exc_info=True,
            )
            return False

    def _extract_weights_from_positions(
        self,
        positions: list[dict[str, Any]],
    ) -> dict[str, float]:
        weights: dict[str, float] = {}

        for position in positions:
            if not isinstance(position, dict):
                continue

            symbol = position.get("symbol")
            if not symbol:
                continue

            target_weight = float(position.get("target_weight", 0.0))
            weights[str(symbol)] = target_weight

        return weights

    def _extract_signals_from_positions(
        self,
        positions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        signal_rows: list[dict[str, Any]] = []

        for position in positions:
            if not isinstance(position, dict):
                continue

            signal_rows.append(
                {
                    "symbol": position.get("symbol"),
                    "score": float(position.get("score", 0.0)),
                    "confidence": float(position.get("confidence", 0.0)),
                    "direction": position.get("direction"),
                    "forecast": position.get("forecast"),
                    "action": position.get("action"),
                    "asset_name": position.get("asset_name"),
                    "asset_class": position.get("asset_class"),
                }
            )

        return signal_rows

    def _serialize_payload_for_storage(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Converts nested structures to JSON strings for SQLite-friendly storage.
        """
        return {
            "user_id": payload["user_id"],
            "snapshot_date": payload["snapshot_date"],
            "generated_at": payload["generated_at"],
            "rebalance_required": int(payload["rebalance_required"]),
            "rebalance_reason": payload["rebalance_reason"],
            "total_invested_weight": payload["total_invested_weight"],
            "cash_weight": payload["cash_weight"],
            "allocation_hint": payload["allocation_hint"],
            "weights": json.dumps(payload["weights"]),
            "positions": json.dumps(payload["positions"]),
            "signals": json.dumps(payload["signals"]),
            "meta": json.dumps(payload["meta"]),
        }

    def _extract_snapshot_date(self, generated_at: str) -> str:
        """
        Converts generated_at to YYYY-MM-DD.
        """
        try:
            normalized = generated_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            return dt.date().isoformat()
        except Exception:
            return datetime.now(timezone.utc).date().isoformat()

    def _utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()