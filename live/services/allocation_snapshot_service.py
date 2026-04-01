from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from live.repository.allocation_repository import AllocationRepository
from services.portfolio_performance_adapter import PortfolioPerformanceAdapter


class AllocationSnapshotService:
    def __init__(self) -> None:
        self.repository = AllocationRepository()
        self.performance_adapter = PortfolioPerformanceAdapter()

    # ---------------------------------------------------
    # MAIN ENTRY
    # ---------------------------------------------------

    def persist_snapshot(
        self,
        user_id: int,
        portfolio: Dict[str, Any],
    ) -> None:

        snapshot_date = datetime.now(timezone.utc).isoformat()

        weights = self._extract_weights(portfolio)
        positions = portfolio.get("positions", [])
        signals = portfolio.get("meta", {}).get("mapping_breakdown", [])
        meta = portfolio.get("meta", {})

        # ✅ IMMER INSERT (kein Upsert!)
        self.repository.insert_snapshot(
            user_id=user_id,
            snapshot_date=snapshot_date,
            weights=weights,
            positions=positions,
            signals=signals,
            meta=meta,
        )

        # 🔥 Performance direkt aktualisieren
        try:
            self.performance_adapter.get_performance_for_user(
                user_id=user_id,
                force_recompute=True,
            )
        except Exception:
            pass

    # ---------------------------------------------------
    # HELPERS
    # ---------------------------------------------------

    def _extract_weights(self, portfolio: Dict[str, Any]) -> Dict[str, float]:
        weights: Dict[str, float] = {}

        for position in portfolio.get("positions", []):
            symbol = position.get("symbol")
            weight = float(position.get("target_weight", 0.0))

            if symbol:
                weights[symbol] = weight

        return weights