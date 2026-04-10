from __future__ import annotations

print(">>> STABLE RANKING VERSION ACTIVE <<<")

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from models.backtest.allocation import (
    DEFAULT_REGIME_ALLOCATION,
    RegimeAllocation,
    build_probabilistic_regime_weights,
)
from models.backtest.portfolio_metrics import summarize_performance
from models.backtest.regime_ranking import RegimeRankingEngine, RankingConfig
from models.backtest.regime_selector import (
    RegimeSelector,
    RegimeSelectorConfig,
    build_regime_frame,
)


# =========================================================
# CONFIG
# =========================================================


@dataclass
class BacktestConfig:
    date_col: str = "date"
    regime_col: str = "regime"
    prob_3m_col: str = "prob_3m"
    prob_6m_col: str = "prob_6m"

    periods_per_year: int = 12
    signal_lag_periods: int = 1
    risk_free_rate: float = 0.0

    
    # Costs (UI-ready, in basis points)
    transaction_cost_bps: float = 5.0   # 0.05%
    slippage_bps: float = 0.0           # optional additional cost
    include_costs: bool = True

    use_conviction_scaling: bool = True
    conviction_floor: float = 0.35

    conviction_method: str = "power"
    conviction_exponent: float = 1.3

    logistic_k: float = 10.0
    logistic_threshold: float = 0.3

    use_vol_targeting: bool = True
    target_annual_vol: float = 0.15
    vol_lookback_periods: int = 12
    max_leverage: float = 2.0

    # Phase C
    use_regime_ranking: bool = False
    ranking_top_n: int = 3
    ranking_lookback_months: int = 24
    ranking_min_history: int = 6

    # Phase 10 / 10.4
    smoothing_alpha: float = 0.30
    gamma: float = 1.35   # 🔥 NEU
    mapper_temperature: float = 0.70


# =========================================================
# ENGINE
# =========================================================


class BacktestEngine:
    def __init__(
        self,
        allocation: Optional[RegimeAllocation] = None,
        config: Optional[BacktestConfig] = None,
        selector: Optional[RegimeSelector] = None,
    ) -> None:
        self.allocation = allocation or DEFAULT_REGIME_ALLOCATION
        self.config = config or BacktestConfig()

        self.selector = selector or RegimeSelector(
            RegimeSelectorConfig(
                min_conviction=self.config.conviction_floor,
                allowed_regimes=("short_term_reflation",),
            )
        )

        self.ranking_engine = RegimeRankingEngine(
            RankingConfig(
                top_n=self.config.ranking_top_n,
                lookback_months=self.config.ranking_lookback_months,
                min_history=self.config.ranking_min_history,
            )
        )

    # =========================================================
    # MAIN RUN
    # =========================================================

    def run(
        self,
        signals_df: pd.DataFrame,
        returns_df: pd.DataFrame,
    ) -> dict:

        signals = self._prepare_signals(signals_df)
        returns = self._prepare_returns(returns_df)

        weights = self._build_weight_frame(signals, returns)

        shifted_weights = weights.shift(self.config.signal_lag_periods)

        aligned_returns, aligned_weights = returns.align(
            shifted_weights, join="inner", axis=0
        )

        aligned_weights = aligned_weights.fillna(0.0)

        portfolio_weights = aligned_weights.copy()
        portfolio_returns = aligned_returns.copy()

        portfolio_weights, leverage = self._apply_vol_targeting(
            portfolio_weights,
            portfolio_returns,
        )

        gross_returns = (portfolio_weights * portfolio_returns).sum(axis=1)

        turnover = portfolio_weights.diff().abs().sum(axis=1).fillna(
            portfolio_weights.abs().sum(axis=1)
        )

        transaction_cost_rate = self.config.transaction_cost_bps / 10000.0
        slippage_cost_rate = self.config.slippage_bps / 10000.0

        if self.config.include_costs:
            transaction_cost_series = turnover * transaction_cost_rate
            slippage_cost_series = turnover * slippage_cost_rate
        else:
            transaction_cost_series = pd.Series(0.0, index=turnover.index)
            slippage_cost_series = pd.Series(0.0, index=turnover.index)

        total_cost_series = transaction_cost_series + slippage_cost_series
        net_returns = gross_returns - total_cost_series

        equity_curve_gross = (1.0 + gross_returns).cumprod()
        equity_curve_net = (1.0 + net_returns).cumprod()

        result_frame = pd.DataFrame(
            {
                "portfolio_gross_return": gross_returns,
                "transaction_cost": transaction_cost_series,
                "slippage_cost": slippage_cost_series,
                "total_cost": total_cost_series,
                "portfolio_net_return": net_returns,
                "equity_curve_gross": equity_curve_gross,
                "equity_curve": equity_curve_net,
                "turnover": turnover,
                "leverage": leverage.reindex(gross_returns.index).fillna(1.0),
            },
            index=aligned_returns.index,
        )

        metrics = summarize_performance(
            returns=net_returns,
            turnover=turnover,
            periods_per_year=self.config.periods_per_year,
            risk_free_rate=self.config.risk_free_rate,
        )

        total_transaction_cost = float(transaction_cost_series.sum())
        total_slippage_cost = float(slippage_cost_series.sum())
        total_cost = float(total_cost_series.sum())
        avg_transaction_cost = float(transaction_cost_series.mean())
        avg_slippage_cost = float(slippage_cost_series.mean())
        avg_total_cost = float(total_cost_series.mean())

        total_gross_return = float(equity_curve_gross.iloc[-1] - 1.0) if len(equity_curve_gross) else 0.0
        total_net_return = float(equity_curve_net.iloc[-1] - 1.0) if len(equity_curve_net) else 0.0
        cost_drag = total_gross_return - total_net_return

        metrics.update(
            {
                "total_gross_return": total_gross_return,
                "total_net_return": total_net_return,
                "total_transaction_cost": total_transaction_cost,
                "total_slippage_cost": total_slippage_cost,
                "total_cost": total_cost,
                "avg_transaction_cost": avg_transaction_cost,
                "avg_slippage_cost": avg_slippage_cost,
                "avg_total_cost": avg_total_cost,
                "cost_drag": cost_drag,
                "transaction_cost_bps": float(self.config.transaction_cost_bps),
                "slippage_bps": float(self.config.slippage_bps),
                "costs_enabled": bool(self.config.include_costs),
            }
        )

        return {
            "timeseries": result_frame.reset_index(),
            "weights": portfolio_weights.reset_index(),
            "metrics": metrics,
        }

    # =========================================================
    # PREP
    # =========================================================

    def _prepare_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df = df.set_index("date")
        else:
            df.index = pd.to_datetime(df.index, utc=True)

        df.index = df.index.tz_convert(None)

        return df.sort_index()

    def _prepare_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df = df.set_index("date")
        else:
            df.index = pd.to_datetime(df.index, utc=True)

        df.index = df.index.tz_convert(None)

        return df.sort_index().astype(float)

    # =========================================================
    # CORE
    # =========================================================

    def _build_weight_frame(
        self,
        signals: pd.DataFrame,
        returns: pd.DataFrame,
    ) -> pd.DataFrame:

        if self.config.use_regime_ranking:
            print(">>> USING REGIME RANKING <<<")
            regime_df = build_regime_frame(signals)
            return self.ranking_engine.build_top_n_weights(regime_df, returns)

        regime_df = signals.copy()

        weights = build_probabilistic_regime_weights(
            regime_df=regime_df,
            regime_allocations=self.allocation,
            assets=list(returns.columns),
            smoothing_alpha=self.config.smoothing_alpha,
            mapper_temperature=self.config.mapper_temperature,
            config=self.config,  # 🔥 DAS ist der Schlüssel
        )

        return weights

    # =========================================================
    # VOL TARGETING
    # =========================================================

    def _apply_vol_targeting(
        self,
        weights: pd.DataFrame,
        returns: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.Series]:
        if not self.config.use_vol_targeting:
            return weights, pd.Series(1.0, index=weights.index)

        base_returns = (weights * returns).sum(axis=1)

        rolling_vol = (
            base_returns.rolling(self.config.vol_lookback_periods).std()
            * np.sqrt(self.config.periods_per_year)
        )

        leverage = (self.config.target_annual_vol / rolling_vol) * 0.7
        leverage = leverage.replace([np.inf, -np.inf], np.nan).fillna(1.0)
        leverage = leverage.clip(0.5, self.config.max_leverage)

        return weights.mul(leverage, axis=0), leverage