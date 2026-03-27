from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from live.repository.performance_repository import (
    PerformanceSnapshotRecord,
    PortfolioPerformanceRepository,
)
from shared.constants.performance_asset_map import PORTFOLIO_TO_RETURN_BUCKET


ANNUALIZATION_FACTOR = 12.0


@dataclass
class PerformanceResult:
    summary: dict[str, Any]
    history: list[dict[str, Any]]
    signal_accuracy: dict[str, Any]
    intelligence: dict[str, Any]


class PerformanceEngineService:
    def __init__(self, repository: PortfolioPerformanceRepository | None = None) -> None:
        self.repository = repository or PortfolioPerformanceRepository()

    def build_performance(
        self,
        user_id: int,
        allocation_snapshots: pd.DataFrame,
        asset_returns: pd.DataFrame,
        signal_history: pd.DataFrame | None = None,
        risk_free_rate_annual: float = 0.0,
        starting_value: float = 100.0,
    ) -> PerformanceResult:
        history_df = self._build_portfolio_history(
            allocation_snapshots=allocation_snapshots,
            asset_returns=asset_returns,
            starting_value=starting_value,
        )

        summary = self._build_summary_metrics(
            history_df=history_df,
            risk_free_rate_annual=risk_free_rate_annual,
        )

        signal_accuracy = self._build_signal_accuracy(
            signal_history=signal_history,
            asset_returns=asset_returns,
        )

        intelligence = self._build_intelligence_overlay(
            history_df=history_df,
            signal_accuracy=signal_accuracy,
        )

        latest = history_df.iloc[-1]

        self.repository.upsert_snapshot(
            PerformanceSnapshotRecord(
                user_id=user_id,
                snapshot_date=str(latest["date"].date()),
                portfolio_value=float(latest["portfolio_value"]),
                period_return=float(latest["period_return"]),
                cumulative_return=float(latest["cumulative_return"]),
                annualized_return=float(summary["annualized_return"]),
                annualized_volatility=float(summary["volatility"]),
                sharpe_ratio=float(summary["sharpe_ratio"]),
                max_drawdown=float(summary["max_drawdown"]),
                hit_rate=float(signal_accuracy["overall_hit_rate"]),
                intelligence=intelligence,
            )
        )

        history_payload = history_df.copy()
        history_payload["date"] = history_payload["date"].dt.strftime("%Y-%m-%d")

        return PerformanceResult(
            summary=summary,
            history=history_payload.to_dict(orient="records"),
            signal_accuracy=signal_accuracy,
            intelligence=intelligence,
        )

    def _build_portfolio_history(
        self,
        allocation_snapshots: pd.DataFrame,
        asset_returns: pd.DataFrame,
        starting_value: float,
    ) -> pd.DataFrame:
        if allocation_snapshots.empty:
            raise ValueError("allocation_snapshots is empty")

        if asset_returns.empty:
            raise ValueError("asset_returns is empty")

        snapshots = allocation_snapshots.copy()
        snapshots["snapshot_date"] = pd.to_datetime(snapshots["snapshot_date"])
        snapshots = snapshots.sort_values("snapshot_date")

        returns_df = asset_returns.copy()
        returns_df.index = pd.to_datetime(returns_df.index)
        returns_df = returns_df.sort_index()

        latest_allowed_date = snapshots["snapshot_date"].max()
        returns_df = returns_df.loc[returns_df.index <= latest_allowed_date]

        if returns_df.empty:
            raise ValueError("No asset return rows available up to latest snapshot_date")

        weights_by_date: dict[pd.Timestamp, dict[str, float]] = {}
        for _, row in snapshots.iterrows():
            weights = row["weights"]
            if isinstance(weights, str):
                weights = json.loads(weights)
            weights_by_date[pd.Timestamp(row["snapshot_date"])] = weights

        rows: list[dict[str, Any]] = []
        portfolio_value = starting_value
        latest_weights: dict[str, float] = {}

        snapshot_dates = sorted(weights_by_date.keys())
        snapshot_idx = 0

        for date, asset_row in returns_df.iterrows():
            while snapshot_idx < len(snapshot_dates) and snapshot_dates[snapshot_idx] <= date:
                latest_weights = weights_by_date[snapshot_dates[snapshot_idx]]
                snapshot_idx += 1

            if not latest_weights:
                continue

            period_return = self._compute_weighted_return(
                weights=latest_weights,
                realized_returns=asset_row.to_dict(),
            )

            portfolio_value *= (1.0 + period_return)

            rows.append(
                {
                    "date": date,
                    "period_return": float(period_return),
                    "portfolio_value": float(portfolio_value),
                    "weights": latest_weights,
                }
            )

        if not rows:
            first_snapshot_date = snapshots["snapshot_date"].min()
            rows = [
                {
                    "date": first_snapshot_date,
                    "period_return": 0.0,
                    "portfolio_value": float(starting_value),
                    "weights": weights_by_date[first_snapshot_date],
                }
            ]

        history_df = pd.DataFrame(rows)
        history_df["cumulative_return"] = history_df["portfolio_value"] / starting_value - 1.0
        history_df["rolling_peak"] = history_df["portfolio_value"].cummax()
        history_df["drawdown"] = history_df["portfolio_value"] / history_df["rolling_peak"] - 1.0

        return history_df

    def _compute_weighted_return(
        self,
        weights: dict[str, float],
        realized_returns: dict[str, float],
    ) -> float:
        total = 0.0

        for asset, weight in weights.items():
            mapped_asset = PORTFOLIO_TO_RETURN_BUCKET.get(asset, asset)
            asset_return = float(realized_returns.get(mapped_asset, 0.0))
            total += float(weight) * asset_return

        return total

    def _build_summary_metrics(
        self,
        history_df: pd.DataFrame,
        risk_free_rate_annual: float,
    ) -> dict[str, Any]:
        rets = history_df["period_return"].astype(float)
        n = len(rets)

        total_return = float((1.0 + rets).prod() - 1.0)
        annualized_return = (
            float((1.0 + total_return) ** (ANNUALIZATION_FACTOR / max(n, 1)) - 1.0)
            if n > 0
            else 0.0
        )

        volatility = float(rets.std(ddof=1) * np.sqrt(ANNUALIZATION_FACTOR)) if n > 1 else 0.0
        rf_periodic = risk_free_rate_annual / ANNUALIZATION_FACTOR
        excess_returns = rets - rf_periodic

        sharpe_ratio = (
            float((excess_returns.mean() * ANNUALIZATION_FACTOR) / volatility)
            if volatility > 0
            else 0.0
        )

        max_drawdown = float(history_df["drawdown"].min())

        return {
            "observations": int(n),
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "latest_value": float(history_df.iloc[-1]["portfolio_value"]),
            "latest_period_return": float(history_df.iloc[-1]["period_return"]),
            "latest_cumulative_return": float(history_df.iloc[-1]["cumulative_return"]),
        }

    def _build_signal_accuracy(
        self,
        signal_history: pd.DataFrame | None,
        asset_returns: pd.DataFrame,
    ) -> dict[str, Any]:
        if signal_history is None or signal_history.empty:
            return {
                "overall_hit_rate": 0.0,
                "total_signals": 0,
                "hits": 0,
                "by_signal": {},
            }

        signals = signal_history.copy()
        signals["date"] = pd.to_datetime(signals["date"])

        returns_df = asset_returns.copy()
        returns_df.index = pd.to_datetime(returns_df.index)
        returns_df = returns_df.sort_index()

        by_signal: dict[str, Any] = {}

        cooling_metrics = self._evaluate_signal_rule(
            signals=signals,
            returns_df=returns_df,
            signal_col="inflation_cooling",
            favorable_assets=["duration_long", "duration_intermediate"],
            defensive_assets=["cash_bonds", "cash"],
            label="Inflation Cooling → Duration Favorable",
        )
        by_signal[cooling_metrics["label"]] = cooling_metrics

        disinflation_metrics = self._evaluate_signal_rule(
            signals=signals,
            returns_df=returns_df,
            signal_col="disinflation_trend",
            favorable_assets=["equities_broad", "quality_equities", "cyclical_equities"],
            defensive_assets=["cash_bonds", "cash"],
            label="Disinflation Trend → Risk Assets Supported",
        )
        by_signal[disinflation_metrics["label"]] = disinflation_metrics

        total_hits = sum(item["hits"] for item in by_signal.values())
        total_signals = sum(item["total"] for item in by_signal.values())
        overall_hit_rate = float(total_hits / total_signals) if total_signals > 0 else 0.0

        return {
            "overall_hit_rate": overall_hit_rate,
            "total_signals": total_signals,
            "hits": total_hits,
            "by_signal": by_signal,
        }

    def _evaluate_signal_rule(
        self,
        signals: pd.DataFrame,
        returns_df: pd.DataFrame,
        signal_col: str,
        favorable_assets: list[str],
        defensive_assets: list[str],
        label: str,
    ) -> dict[str, Any]:
        if signal_col not in signals.columns:
            return {"label": label, "hits": 0, "total": 0, "hit_rate": 0.0}

        active_rows = signals.loc[signals[signal_col] == 1].copy()
        if active_rows.empty:
            return {"label": label, "hits": 0, "total": 0, "hit_rate": 0.0}

        hits = 0
        total = 0

        for _, row in active_rows.iterrows():
            current_date = pd.Timestamp(row["date"])
            future_dates = returns_df.index[returns_df.index > current_date]
            if len(future_dates) == 0:
                continue

            next_date = future_dates[0]
            next_returns = returns_df.loc[next_date]

            favorable_return = self._basket_return(next_returns, favorable_assets)
            defensive_return = self._basket_return(next_returns, defensive_assets)

            total += 1
            if favorable_return > defensive_return:
                hits += 1

        hit_rate = float(hits / total) if total > 0 else 0.0
        return {
            "label": label,
            "hits": hits,
            "total": total,
            "hit_rate": hit_rate,
        }

    def _basket_return(self, row: pd.Series, assets: list[str]) -> float:
        available = [asset for asset in assets if asset in row.index]
        if not available:
            return 0.0
        return float(np.mean([float(row[a]) for a in available]))

    def _build_intelligence_overlay(
        self,
        history_df: pd.DataFrame,
        signal_accuracy: dict[str, Any],
    ) -> dict[str, Any]:
        latest_drawdown = float(history_df.iloc[-1]["drawdown"])
        recent_3m = history_df["period_return"].tail(3)
        recent_momentum = float((1.0 + recent_3m).prod() - 1.0) if not recent_3m.empty else 0.0

        cooling_hit_rate = signal_accuracy["by_signal"].get(
            "Inflation Cooling → Duration Favorable", {}
        ).get("hit_rate", 0.0)

        disinflation_hit_rate = signal_accuracy["by_signal"].get(
            "Disinflation Trend → Risk Assets Supported", {}
        ).get("hit_rate", 0.0)

        narratives: list[dict[str, Any]] = []

        narratives.append(
            {
                "title": "Inflation Cooling → Duration Favorable",
                "status": "confirmed" if cooling_hit_rate >= 0.55 else "monitor",
                "hit_rate": cooling_hit_rate,
                "message": (
                    "Duration exposure has historically responded well when inflation cooling signals were active."
                    if cooling_hit_rate >= 0.55
                    else "Duration tailwind exists, but empirical confirmation is still moderate."
                ),
            }
        )

        narratives.append(
            {
                "title": "Disinflation Trend → Risk Assets Supported",
                "status": "confirmed" if disinflation_hit_rate >= 0.55 else "monitor",
                "hit_rate": disinflation_hit_rate,
                "message": (
                    "Risk assets were generally supported when disinflation trend signals were active."
                    if disinflation_hit_rate >= 0.55
                    else "Risk asset support is present, but still needs stronger realized confirmation."
                ),
            }
        )

        return {
            "recent_3m_momentum": recent_momentum,
            "current_drawdown": latest_drawdown,
            "signal_backing_strength": signal_accuracy["overall_hit_rate"],
            "narratives": narratives,
        }