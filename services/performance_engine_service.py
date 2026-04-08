from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional

import pandas as pd

from live.repository.allocation_repository import AllocationRepository
from services.alpha_intelligence_service import AlphaIntelligenceService


# ---------------------------------------------------
# ETF → Macro Return Mapping
# ---------------------------------------------------

ETF_TO_RETURN_KEY = {
    "SPY": "equities_broad",
    "QQQ": "equities_broad",
    "IEF": "duration_intermediate",
    "TLT": "duration_long",
    "SHY": "cash_bonds",
    "GLD": "gold",
    "DBC": "commodities",
    "TIP": "tips",
    "CASH": "cash",
}

VALID_ASSETS = set(ETF_TO_RETURN_KEY.keys())


# ---------------------------------------------------
# BENCHMARK CONFIG
# ---------------------------------------------------

DEFAULT_BENCHMARK_WEIGHTS = {
    "SPY": 0.60,
    "IEF": 0.40,
}


# ---------------------------------------------------
# RESULT OBJECT
# ---------------------------------------------------

class PerformanceResult:
    def __init__(
        self,
        summary: Dict[str, Any],
        history: List[Dict[str, Any]],
        signal_accuracy: Dict[str, Any],
        intelligence: Dict[str, Any],
        meta: Dict[str, Any],
        alpha_intelligence: Dict[str, Any],
    ):
        self.summary = summary
        self.history = history
        self.signal_accuracy = signal_accuracy
        self.intelligence = intelligence
        self.meta = meta
        self.alpha_intelligence = alpha_intelligence


# ---------------------------------------------------
# MAIN SERVICE
# ---------------------------------------------------

class PerformanceEngineService:
    def __init__(self, repository: Optional[AllocationRepository] = None):
        self.repository = repository or AllocationRepository()
        self.alpha_service = AlphaIntelligenceService()
        self.returns_df = self._load_asset_returns()

    # ---------------------------------------------------
    # SERIALIZATION / OUTPUT HARDENING
    # ---------------------------------------------------

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, pd.Timestamp):
            return value.isoformat()

        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return float(value)

        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]

        if isinstance(value, tuple):
            return [self._serialize_value(v) for v in value]

        return value

    def _serialize_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []

        records = df.to_dict(orient="records")
        return [self._serialize_value(record) for record in records]

    # ---------------------------------------------------
    # LOAD RETURNS
    # ---------------------------------------------------

    def _load_asset_returns(self) -> pd.DataFrame:
        try:
            df = pd.read_csv("storage/cache/asset_returns.csv")

            df.columns = df.columns.str.strip().str.lower()

            df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
            df = df.dropna(subset=["date"])
            df = df.sort_values("date")
            df["month"] = df["date"].dt.tz_localize(None).dt.to_period("M")

            return df
        except Exception:
            return pd.DataFrame()

    def _get_returns_for_date(self, date: pd.Timestamp) -> Optional[pd.Series]:
        if pd.isna(date) or self.returns_df.empty:
            return None

        target_month = date.tz_localize(None).to_period("M")
        df = self.returns_df[self.returns_df["month"] <= target_month]

        if df.empty:
            return None

        return df.iloc[-1]

    # ---------------------------------------------------
    # SNAPSHOT CLEANING + MONTHLY BACKFILL
    # ---------------------------------------------------

    def _clean_snapshots(self, df: pd.DataFrame) -> pd.DataFrame:
        cleaned_rows = []

        for _, row in df.iterrows():
            weights = row.get("weights")

            if isinstance(weights, str):
                try:
                    weights = json.loads(weights)
                except Exception:
                    continue

            if not isinstance(weights, dict):
                continue

            filtered = {
                k: float(v)
                for k, v in weights.items()
                if k in VALID_ASSETS and v is not None
            }

            if not filtered:
                continue

            cleaned_rows.append(
                {
                    "snapshot_date": row["snapshot_date"],
                    "weights": filtered,
                    "meta": row.get("meta"),
                }
            )

        if not cleaned_rows:
            return pd.DataFrame()

        df_clean = pd.DataFrame(cleaned_rows)
        df_clean = df_clean.sort_values("snapshot_date").reset_index(drop=True)

        df_clean["month"] = (
            df_clean["snapshot_date"]
            .dt.tz_localize(None)
            .dt.to_period("M")
        )

        monthly = (
            df_clean
            .groupby("month", as_index=False)
            .tail(1)
            .sort_values("snapshot_date")
            .reset_index(drop=True)
        )

        if monthly.empty:
            return pd.DataFrame()

        start_month = monthly["month"].min()
        end_month = monthly["month"].max()
        full_months = pd.period_range(start=start_month, end=end_month, freq="M")

        monthly_lookup: Dict[pd.Period, Dict[str, Any]] = {}
        for _, row in monthly.iterrows():
            monthly_lookup[row["month"]] = {
                "weights": row["weights"],
                "meta": row.get("meta"),
            }

        last_weights = None
        last_meta = None
        filled_rows = []

        for month in full_months:
            if month in monthly_lookup:
                last_weights = monthly_lookup[month]["weights"]
                last_meta = monthly_lookup[month]["meta"]

            if last_weights is None:
                continue

            month_end = pd.Timestamp(month.to_timestamp("M")).tz_localize("UTC")

            filled_rows.append(
                {
                    "snapshot_date": month_end,
                    "weights": last_weights,
                    "meta": last_meta,
                }
            )

        if not filled_rows:
            return pd.DataFrame()

        result = pd.DataFrame(filled_rows)
        result = result.sort_values("snapshot_date").reset_index(drop=True)

        return result

    # ---------------------------------------------------
    # MAIN
    # ---------------------------------------------------

    def build_performance(
        self,
        user_id: int,
        risk_free_rate_annual: float = 0.0,
        transaction_cost_bps: float = 10.0,
    ) -> PerformanceResult:

        snapshots = self.repository.get_snapshots_by_user(user_id)

        if not snapshots:
            return PerformanceResult({}, [], {}, {}, {"source": "empty"}, {})

        df = pd.DataFrame(snapshots)

        if "snapshot_date" not in df.columns and "generated_at" in df.columns:
            df["snapshot_date"] = df["generated_at"]

        df["snapshot_date"] = pd.to_datetime(
            df["snapshot_date"], errors="coerce", utc=True
        )
        df = df.dropna(subset=["snapshot_date"])
        df = df.sort_values("snapshot_date")

        df = self._clean_snapshots(df)

        if df.empty:
            return PerformanceResult({}, [], {}, {}, {"source": "clean_empty"}, {})

        base_history = self._build_portfolio_history(
            df=df,
            transaction_cost_bps=transaction_cost_bps,
        )
        risk_history = self._build_risk_adjusted_history(
            df=df,
            transaction_cost_bps=transaction_cost_bps,
        )
        benchmark_history = self._build_benchmark_history(df)

        base_summary = self._build_summary(base_history)

        risk_summary = None
        if not risk_history.empty:
            risk_summary = self._build_summary(risk_history)

        benchmark_summary = None
        if not benchmark_history.empty:
            benchmark_summary = self._build_summary(benchmark_history)

        alpha_analysis = {}
        if base_summary and risk_summary:
            alpha_analysis = self._compute_alpha_metrics(
                base_summary,
                risk_summary,
            )

        benchmark_alpha_analysis = {}
        if base_summary and benchmark_summary:
            benchmark_alpha_analysis = self._compute_benchmark_alpha_metrics(
                portfolio=base_summary,
                benchmark=benchmark_summary,
            )

        rolling_benchmark_analytics = self._build_rolling_benchmark_analytics(
            portfolio_history=base_history,
            benchmark_history=benchmark_history,
        )

        attribution_intelligence = self._build_attribution_intelligence(base_history)

        benchmark_intelligence = self._build_benchmark_intelligence(
            portfolio_summary=base_summary,
            benchmark_summary=benchmark_summary,
            rolling_benchmark_analytics=rolling_benchmark_analytics,
        )

        alpha_intelligence = self.alpha_service.build_alpha_intelligence(
            base_history=base_history,
            risk_history=risk_history,
            snapshots_df=df,
        )

        result = PerformanceResult(
            summary={
                "base": base_summary,
                "risk_adjusted": risk_summary,
                "benchmark": benchmark_summary,
                "alpha_analysis": alpha_analysis,
                "benchmark_alpha_analysis": benchmark_alpha_analysis,
                "rolling_benchmark_analytics": rolling_benchmark_analytics,
            },
            history=self._serialize_dataframe(base_history),
            signal_accuracy={
                "overall_hit_rate": 0.0,
                "total_signals": 0,
                "hits": 0,
                "by_signal": {},
            },
            intelligence={
                "recent_3m_momentum": base_summary.get("total_return", 0.0),
                "current_drawdown": base_summary.get("max_drawdown", 0.0),
                "attribution": attribution_intelligence,
                "benchmark": benchmark_intelligence,
                "narratives": self._build_narratives(
                    attribution_intelligence=attribution_intelligence,
                    benchmark_intelligence=benchmark_intelligence,
                ),
            },
            meta={
                "source": "db_backfilled",
                "observations": len(base_history),
                "benchmark_name": "60_40_spy_ief",
                "transaction_cost_bps": transaction_cost_bps,
            },
            alpha_intelligence=alpha_intelligence,
        )

        result.summary = self._serialize_value(result.summary)
        result.signal_accuracy = self._serialize_value(result.signal_accuracy)
        result.intelligence = self._serialize_value(result.intelligence)
        result.meta = self._serialize_value(result.meta)
        result.alpha_intelligence = self._serialize_value(result.alpha_intelligence)

        return result

    # ---------------------------------------------------
    # RETURN ENGINE
    # ---------------------------------------------------

    def _compute_portfolio_return(
        self,
        weights: Dict[str, float],
        returns_row: Optional[pd.Series],
    ) -> float:
        if returns_row is None:
            return 0.0

        total_return = 0.0

        for asset, weight in weights.items():
            mapped_key = ETF_TO_RETURN_KEY.get(asset)

            if not mapped_key:
                continue

            asset_return = float(returns_row.get(mapped_key, 0.0) or 0.0)
            total_return += weight * asset_return

        return total_return

    def _compute_asset_contributions(
        self,
        weights: Dict[str, float],
        returns_row: Optional[pd.Series],
    ) -> Dict[str, float]:
        contributions = {}

        if returns_row is None:
            return contributions

        for asset, weight in weights.items():
            mapped_key = ETF_TO_RETURN_KEY.get(asset)

            if not mapped_key:
                continue

            asset_return = float(returns_row.get(mapped_key, 0.0) or 0.0)
            contributions[asset] = weight * asset_return

        return contributions

    def _compute_turnover(
        self,
        previous_weights: Optional[Dict[str, float]],
        current_weights: Dict[str, float],
    ) -> float:
        if previous_weights is None:
            return 0.0

        all_assets = set(previous_weights.keys()) | set(current_weights.keys())

        turnover = 0.0
        for asset in all_assets:
            prev_w = float(previous_weights.get(asset, 0.0))
            curr_w = float(current_weights.get(asset, 0.0))
            turnover += abs(curr_w - prev_w)

        return float(turnover)

    def _compute_transaction_cost(
        self,
        turnover: float,
        transaction_cost_bps: float,
    ) -> float:
        if turnover <= 0:
            return 0.0

        cost_rate = float(transaction_cost_bps) / 10000.0
        return float(turnover * cost_rate)

    # ---------------------------------------------------
    # BASE HISTORY
    # ---------------------------------------------------

    def _build_portfolio_history(
        self,
        df: pd.DataFrame,
        transaction_cost_bps: float = 10.0,
    ) -> pd.DataFrame:
        rows = []
        portfolio_value = 100.0
        previous_weights: Optional[Dict[str, float]] = None

        for _, row in df.iterrows():
            weights = row["weights"]
            returns_row = self._get_returns_for_date(row["snapshot_date"])

            gross_period_return = self._compute_portfolio_return(
                weights,
                returns_row,
            )

            contributions = self._compute_asset_contributions(
                weights,
                returns_row,
            )

            turnover = self._compute_turnover(
                previous_weights=previous_weights,
                current_weights=weights,
            )
            transaction_cost = self._compute_transaction_cost(
                turnover=turnover,
                transaction_cost_bps=transaction_cost_bps,
            )

            net_period_return = gross_period_return - transaction_cost

            portfolio_value *= (1.0 + net_period_return)

            rows.append(
                {
                    "date": row["snapshot_date"],
                    "portfolio_value": portfolio_value,
                    "gross_period_return": gross_period_return,
                    "transaction_cost": transaction_cost,
                    "turnover": turnover,
                    "period_return": net_period_return,
                    "contributions": contributions,
                }
            )

            previous_weights = dict(weights)

        result = pd.DataFrame(rows)

        if result.empty:
            return result

        result["cumulative_return"] = result["portfolio_value"] / 100.0 - 1.0
        result["rolling_peak"] = result["portfolio_value"].cummax()
        result["drawdown"] = result["portfolio_value"] / result["rolling_peak"] - 1.0

        return result

    # ---------------------------------------------------
    # BENCHMARK HISTORY
    # ---------------------------------------------------

    def _build_benchmark_history(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        benchmark_value = 100.0

        for _, row in df.iterrows():
            returns_row = self._get_returns_for_date(row["snapshot_date"])

            period_return = self._compute_portfolio_return(
                DEFAULT_BENCHMARK_WEIGHTS,
                returns_row,
            )

            benchmark_value *= (1.0 + period_return)

            rows.append(
                {
                    "date": row["snapshot_date"],
                    "portfolio_value": benchmark_value,
                    "period_return": period_return,
                }
            )

        result = pd.DataFrame(rows)

        if result.empty:
            return result

        result["cumulative_return"] = result["portfolio_value"] / 100.0 - 1.0
        result["rolling_peak"] = result["portfolio_value"].cummax()
        result["drawdown"] = result["portfolio_value"] / result["rolling_peak"] - 1.0

        return result

    # ---------------------------------------------------
    # ATTRIBUTION INTELLIGENCE
    # ---------------------------------------------------

    def _build_attribution_intelligence(
        self,
        history_df: pd.DataFrame,
    ) -> Dict[str, Any]:

        if history_df.empty:
            return {}

        agg = defaultdict(float)

        for _, row in history_df.iterrows():
            for asset, val in row["contributions"].items():
                agg[asset] += val

        if not agg:
            return {}

        positive = [(a, v) for a, v in agg.items() if v > 0]
        negative = [(a, v) for a, v in agg.items() if v < 0]

        positive_sorted = sorted(positive, key=lambda x: x[1], reverse=True)
        negative_sorted = sorted(negative, key=lambda x: x[1])

        top_positive = positive_sorted[:3]
        top_negative = negative_sorted[:3]

        dominant_driver = min(agg, key=agg.get)

        if negative and not positive:
            narrative = f"All assets detracted from performance, led by {dominant_driver}."
        elif positive and not negative:
            narrative = f"Performance was driven by gains across assets, led by {max(agg, key=agg.get)}."
        else:
            narrative = f"Performance was primarily driven by losses in {dominant_driver} exposure."

        total_transaction_cost = 0.0
        if "transaction_cost" in history_df.columns:
            total_transaction_cost = float(history_df["transaction_cost"].sum())

        return {
            "top_negative": top_negative,
            "top_positive": top_positive,
            "dominant_driver": dominant_driver,
            "total_contributions": dict(agg),
            "total_transaction_cost": total_transaction_cost,
            "narrative": narrative,
        }

    # ---------------------------------------------------
    # RISK HISTORY
    # ---------------------------------------------------

    def _build_risk_adjusted_history(
        self,
        df: pd.DataFrame,
        transaction_cost_bps: float = 10.0,
    ) -> pd.DataFrame:
        rows = []
        portfolio_value = 100.0
        previous_weights: Optional[Dict[str, float]] = None

        for _, row in df.iterrows():
            meta = row.get("meta")

            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    continue

            risk_overlay = meta.get("risk_overlay") if meta else None

            if not risk_overlay:
                continue

            allocations = risk_overlay.get("adjusted_allocations", [])

            weights = {
                item["asset"]: item["adjusted_weight"]
                for item in allocations
                if item.get("asset") in VALID_ASSETS
            }

            returns_row = self._get_returns_for_date(row["snapshot_date"])

            gross_period_return = self._compute_portfolio_return(
                weights,
                returns_row,
            )

            turnover = self._compute_turnover(
                previous_weights=previous_weights,
                current_weights=weights,
            )
            transaction_cost = self._compute_transaction_cost(
                turnover=turnover,
                transaction_cost_bps=transaction_cost_bps,
            )

            net_period_return = gross_period_return - transaction_cost

            portfolio_value *= (1.0 + net_period_return)

            rows.append(
                {
                    "date": row["snapshot_date"],
                    "portfolio_value": portfolio_value,
                    "gross_period_return": gross_period_return,
                    "transaction_cost": transaction_cost,
                    "turnover": turnover,
                    "period_return": net_period_return,
                }
            )

            previous_weights = dict(weights)

        result = pd.DataFrame(rows)

        if result.empty:
            return result

        result["cumulative_return"] = result["portfolio_value"] / 100.0 - 1.0
        result["rolling_peak"] = result["portfolio_value"].cummax()
        result["drawdown"] = result["portfolio_value"] / result["rolling_peak"] - 1.0

        return result

    # ---------------------------------------------------
    # BENCHMARK INTELLIGENCE
    # ---------------------------------------------------

    def _build_benchmark_intelligence(
        self,
        portfolio_summary: Dict[str, Any],
        benchmark_summary: Optional[Dict[str, Any]],
        rolling_benchmark_analytics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not portfolio_summary or not benchmark_summary:
            return {}

        portfolio_return = float(portfolio_summary.get("total_return", 0.0))
        benchmark_return = float(benchmark_summary.get("total_return", 0.0))
        alpha = portfolio_return - benchmark_return

        if alpha > 0:
            narrative = f"Portfolio outperformed the benchmark by {alpha:.2%}."
        elif alpha < 0:
            narrative = f"Portfolio underperformed the benchmark by {abs(alpha):.2%}."
        else:
            narrative = "Portfolio performed in line with the benchmark."

        result = {
            "portfolio_total_return": portfolio_return,
            "benchmark_total_return": benchmark_return,
            "alpha": alpha,
            "narrative": narrative,
        }

        if rolling_benchmark_analytics:
            result["tracking_error"] = rolling_benchmark_analytics.get("tracking_error")
            result["information_ratio"] = rolling_benchmark_analytics.get("information_ratio")
            result["latest_rolling_alpha"] = rolling_benchmark_analytics.get("latest_rolling_alpha")

        return result

    def _build_narratives(
        self,
        attribution_intelligence: Dict[str, Any],
        benchmark_intelligence: Dict[str, Any],
    ) -> List[str]:
        narratives: List[str] = []

        attribution_narrative = attribution_intelligence.get("narrative")
        if attribution_narrative:
            narratives.append(attribution_narrative)

        benchmark_narrative = benchmark_intelligence.get("narrative")
        if benchmark_narrative:
            narratives.append(benchmark_narrative)

        tracking_error = benchmark_intelligence.get("tracking_error")
        information_ratio = benchmark_intelligence.get("information_ratio")

        if tracking_error is not None:
            narratives.append(f"Tracking error vs benchmark is {tracking_error:.2%}.")

        if information_ratio is not None:
            narratives.append(f"Information ratio is {information_ratio:.2f}.")

        total_transaction_cost = attribution_intelligence.get("total_transaction_cost")
        if total_transaction_cost is not None:
            narratives.append(f"Total transaction cost drag was {total_transaction_cost:.2%}.")

        return narratives

    # ---------------------------------------------------
    # ROLLING / TRACKING ANALYTICS
    # ---------------------------------------------------

    def _build_rolling_benchmark_analytics(
        self,
        portfolio_history: pd.DataFrame,
        benchmark_history: pd.DataFrame,
        window: int = 3,
    ) -> Dict[str, Any]:
        if portfolio_history.empty or benchmark_history.empty:
            return {}

        merged = self._merge_portfolio_and_benchmark_history(
            portfolio_history=portfolio_history,
            benchmark_history=benchmark_history,
        )

        if merged.empty:
            return {}

        merged["active_return"] = (
            merged["portfolio_period_return"] - merged["benchmark_period_return"]
        )

        rolling_window = max(int(window), 1)

        merged["rolling_alpha"] = (
            merged["portfolio_cumulative_return"] - merged["benchmark_cumulative_return"]
        )

        merged["rolling_tracking_error"] = (
            merged["active_return"].rolling(rolling_window).std()
        )

        merged["rolling_information_ratio"] = (
            merged["active_return"].rolling(rolling_window).mean()
            / merged["rolling_tracking_error"].replace(0, pd.NA)
        )

        tracking_error = None
        if len(merged) > 1:
            te = merged["active_return"].std()
            if pd.notna(te):
                tracking_error = float(te)

        information_ratio = None
        if tracking_error is not None and tracking_error > 0:
            information_ratio = float(merged["active_return"].mean() / tracking_error)

        latest_rolling_alpha = None
        if not merged["rolling_alpha"].empty:
            latest_rolling_alpha = float(merged["rolling_alpha"].iloc[-1])

        return {
            "window": rolling_window,
            "tracking_error": tracking_error,
            "information_ratio": information_ratio,
            "latest_rolling_alpha": latest_rolling_alpha,
            "history": self._serialize_dataframe(
                merged[
                    [
                        "date",
                        "portfolio_period_return",
                        "benchmark_period_return",
                        "active_return",
                        "portfolio_cumulative_return",
                        "benchmark_cumulative_return",
                        "rolling_alpha",
                        "rolling_tracking_error",
                        "rolling_information_ratio",
                    ]
                ]
            ),
        }

    def _merge_portfolio_and_benchmark_history(
        self,
        portfolio_history: pd.DataFrame,
        benchmark_history: pd.DataFrame,
    ) -> pd.DataFrame:
        if portfolio_history.empty or benchmark_history.empty:
            return pd.DataFrame()

        portfolio_df = portfolio_history.copy()
        benchmark_df = benchmark_history.copy()

        portfolio_df = portfolio_df.rename(
            columns={
                "period_return": "portfolio_period_return",
                "cumulative_return": "portfolio_cumulative_return",
                "portfolio_value": "portfolio_value_base",
            }
        )

        benchmark_df = benchmark_df.rename(
            columns={
                "period_return": "benchmark_period_return",
                "cumulative_return": "benchmark_cumulative_return",
                "portfolio_value": "portfolio_value_benchmark",
            }
        )

        merged = pd.merge(
            portfolio_df[
                [
                    "date",
                    "portfolio_period_return",
                    "portfolio_cumulative_return",
                    "portfolio_value_base",
                ]
            ],
            benchmark_df[
                [
                    "date",
                    "benchmark_period_return",
                    "benchmark_cumulative_return",
                    "portfolio_value_benchmark",
                ]
            ],
            on="date",
            how="inner",
        )

        merged = merged.sort_values("date").reset_index(drop=True)

        return merged

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

        total_transaction_cost = 0.0
        avg_turnover = 0.0

        if "transaction_cost" in df.columns:
            total_transaction_cost = float(df["transaction_cost"].sum())

        if "turnover" in df.columns and len(df) > 0:
            avg_turnover = float(df["turnover"].mean())

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
            "total_transaction_cost": total_transaction_cost,
            "average_turnover": avg_turnover,
        }

    # ---------------------------------------------------
    # ALPHA
    # ---------------------------------------------------

    def _compute_alpha_metrics(
        self,
        base: Dict[str, Any],
        risk: Dict[str, Any],
    ) -> Dict[str, float]:
        if not base or not risk:
            return {}

        base_return = float(base.get("total_return", 0.0))
        risk_return = float(risk.get("total_return", 0.0))

        base_vol = float(base.get("volatility", 0.0))
        risk_vol = float(risk.get("volatility", 0.0))

        base_dd = float(base.get("max_drawdown", 0.0))
        risk_dd = float(risk.get("max_drawdown", 0.0))

        return_delta = risk_return - base_return

        volatility_reduction = (
            (base_vol - risk_vol) / base_vol if base_vol != 0 else 0.0
        )

        drawdown_reduction = (
            (base_dd - risk_dd) / base_dd if base_dd != 0 else 0.0
        )

        denom = abs(volatility_reduction) + abs(drawdown_reduction)
        efficiency_score = return_delta / denom if denom != 0 else 0.0

        return {
            "return_delta": return_delta,
            "volatility_reduction": volatility_reduction,
            "drawdown_reduction": drawdown_reduction,
            "efficiency_score": efficiency_score,
        }

    def _compute_benchmark_alpha_metrics(
        self,
        portfolio: Dict[str, Any],
        benchmark: Dict[str, Any],
    ) -> Dict[str, float]:
        if not portfolio or not benchmark:
            return {}

        portfolio_return = float(portfolio.get("total_return", 0.0))
        benchmark_return = float(benchmark.get("total_return", 0.0))

        portfolio_vol = float(portfolio.get("volatility", 0.0))
        benchmark_vol = float(benchmark.get("volatility", 0.0))

        portfolio_dd = float(portfolio.get("max_drawdown", 0.0))
        benchmark_dd = float(benchmark.get("max_drawdown", 0.0))

        alpha = portfolio_return - benchmark_return
        volatility_delta = portfolio_vol - benchmark_vol
        drawdown_delta = portfolio_dd - benchmark_dd

        return {
            "alpha": alpha,
            "benchmark_return": benchmark_return,
            "portfolio_return": portfolio_return,
            "volatility_delta": volatility_delta,
            "drawdown_delta": drawdown_delta,
        }