from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

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
        snapshot_date: Optional[str] = None,  # 🔥 NEU (Backfill Support)
    ) -> None:

        now = datetime.now(timezone.utc)

        # ---------------------------------------------------
        # SNAPSHOT DATE LOGIC
        # ---------------------------------------------------

        if snapshot_date:
            # 👉 Backfill Mode (extern vorgegeben)
            dt = datetime.fromisoformat(snapshot_date.replace("Z", "+00:00"))
            snapshot_date_final = self._to_month_end(dt)
            snapshot_mode = "backfill"
        else:
            # 👉 Live Mode (jetzt)
            snapshot_date_final = self._to_month_end(now)
            snapshot_mode = "live"

        # ---------------------------------------------------
        # DATA EXTRACTION
        # ---------------------------------------------------

        weights = self._extract_weights(portfolio)
        positions = portfolio.get("positions", [])
        signals = portfolio.get("meta", {}).get("mapping_breakdown", [])
        meta = portfolio.get("meta", {}) or {}

        # optional Debug / Audit
        meta["generated_at"] = now.isoformat()
        meta["snapshot_mode"] = snapshot_mode

        # ---------------------------------------------------
        # INSERT
        # ---------------------------------------------------

        self.repository.insert_snapshot(
            user_id=user_id,
            snapshot_date=snapshot_date_final,
            weights=weights,
            positions=positions,
            signals=signals,
            meta=meta,
        )

        # ---------------------------------------------------
        # PERFORMANCE TRIGGER
        # ---------------------------------------------------

        try:
            self.performance_adapter.get_performance_for_user(
                user_id=user_id,
                force_recompute=True,
            )
        except Exception:
            pass

    # ---------------------------------------------------
    # MONTH-END NORMALIZATION (CRITICAL)
    # ---------------------------------------------------

    def _to_month_end(self, dt: datetime) -> str:
        """
        Wandelt jedes Datum in Monatsende um (UTC)
        Beispiel:
        2026-04-03 -> 2026-04-30T00:00:00+00:00
        """

        if dt.month == 12:
            next_month = datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)

        month_end = next_month - timedelta(days=1)

        return month_end.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ).isoformat()

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