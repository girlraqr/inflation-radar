from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd

from live.repository.allocation_repository import AllocationRepository


class PerformanceResult:
    def __init__(
        self,
        summary: Dict[str, Any],
        history: List[Dict[str, Any]],
        signal_accuracy: Dict[str, Any],
        intelligence: Dict[str, Any],
        meta: Dict[str, Any],
    ):
        self.summary = summary
        self.history = history
        self.signal_accuracy = signal_accuracy
        self.intelligence = intelligence
        self.meta = meta


class PerformanceEngineService:
    def __init__(self, repository: Optional[AllocationRepository] = None):
        self.repository = repository or AllocationRepository()

    # ---------------------------------------------------
    # MAIN
    # ---------------------------------------------------

    def build_performance(
        self,
        user_id: int,
        risk_free_rate_annual: float = 0.0,
    ) -> PerformanceResult:

        snapshots = self.repository.get_snapshots_by_user(user_id)

        if not snapshots:
            return PerformanceResult({}, [], {}, {}, {"source": "empty"})

        df = pd.DataFrame(snapshots)

        # 🔥 FIX: robuste Datumsbehandlung
        if "snapshot_date" not in df.columns:
            if "generated_at" in df.columns:
                df["snapshot_date"] = df["generated_at"]

        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
        df = df.sort_values("snapshot_date")

        # ---------------------------------------------------
        # BASE HISTORY
        # ---------------------------------------------------

        base_history = self._build_portfolio_history(df)

        # ---------------------------------------------------
        # RISK HISTORY
        # ---------------------------------------------------

        risk_history = self._build_risk_adjusted_history(df)

        # ---------------------------------------------------
        # SUMMARY
        # ---------------------------------------------------

        base_summary = self._build_summary(base_history)

        risk_summary = None
        if not risk_history.empty:
            risk_summary = self._build_summary(risk_history)

        # ---------------------------------------------------
        # RETURN
        # ---------------------------------------------------

        return PerformanceResult(
            summary={
                "base": base_summary,
                "risk_adjusted": risk_summary,
            },
            history=base_history.to_dict(orient="records"),
            signal_accuracy={
                "overall_hit_rate": 0.0,
                "total_signals": 0,
                "hits": 0,
                "by_signal": {},
            },
            intelligence={
                "recent_3m_momentum": base_summary.get("total_return", 0.0),
                "current_drawdown": base_summary.get("max_drawdown", 0.0),
                "signal_backing_strength": 0.0,
                "narratives": [],
            },
            meta={
                "source": "db",
                "observations": len(base_history),
            },
        )

    # ---------------------------------------------------
    # BASE HISTORY
    # ---------------------------------------------------

    def _build_portfolio_history(self, df: pd.DataFrame) -> pd.DataFrame:

        rows = []
        portfolio_value = 100.0

        for _, row in df.iterrows():
            weights = row.get("weights", {})

            if isinstance(weights, str):
                weights = json.loads(weights)

            # 🔥 Dummy Return (ersetzen mit echten Returns später)
            period_return = sum(weights.values()) * 0.01

            portfolio_value *= (1.0 + period_return)

            rows.append(
                {
                    "date": row["snapshot_date"],
                    "portfolio_value": portfolio_value,
                    "period_return": period_return,
                }
            )

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows)
        result["cumulative_return"] = result["portfolio_value"] / 100.0 - 1.0
        result["rolling_peak"] = result["portfolio_value"].cummax()
        result["drawdown"] = result["portfolio_value"] / result["rolling_peak"] - 1.0

        return result

    # ---------------------------------------------------
    # RISK HISTORY
    # ---------------------------------------------------

    def _build_risk_adjusted_history(self, df: pd.DataFrame) -> pd.DataFrame:

        rows = []
        portfolio_value = 100.0

        for _, row in df.iterrows():
            meta = row.get("meta")

            if isinstance(meta, str):
                meta = json.loads(meta)

            risk_overlay = meta.get("risk_overlay") if meta else None

            if not risk_overlay:
                continue

            allocations = risk_overlay.get("adjusted_allocations", [])

            weights = {
                item["asset"]: item["adjusted_weight"]
                for item in allocations
            }

            # 🔥 Dummy Return (ersetzen später)
            period_return = sum(weights.values()) * 0.008

            portfolio_value *= (1.0 + period_return)

            rows.append(
                {
                    "date": row["snapshot_date"],
                    "portfolio_value": portfolio_value,
                    "period_return": period_return,
                }
            )

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows)
        result["cumulative_return"] = result["portfolio_value"] / 100.0 - 1.0
        result["rolling_peak"] = result["portfolio_value"].cummax()
        result["drawdown"] = result["portfolio_value"] / result["rolling_peak"] - 1.0

        return result

    # ---------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------

    def _build_summary(self, df: pd.DataFrame) -> Dict[str, Any]:

        if df.empty:
            return {}

        total_return = df["cumulative_return"].iloc[-1]
        volatility = df["period_return"].std() if len(df) > 1 else 0.0

        sharpe = 0.0
        if volatility > 0:
            sharpe = (df["period_return"].mean() / volatility) * (252**0.5)

        return {
            "observations": len(df),
            "total_return": float(total_return),
            "annualized_return": float(total_return),
            "volatility": float(volatility),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(df["drawdown"].min()),
            "latest_value": float(df["portfolio_value"].iloc[-1]),
            "latest_period_return": float(df["period_return"].iloc[-1]),
            "latest_cumulative_return": float(total_return),
        }