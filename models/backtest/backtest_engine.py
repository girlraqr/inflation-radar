from __future__ import annotations
print(">>> STABLE RANKING VERSION ACTIVE <<<")
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from models.backtest.allocation import DEFAULT_REGIME_ALLOCATION, RegimeAllocation
from models.backtest.conviction import compute_conviction, scale_conviction
from models.backtest.portfolio_metrics import summarize_performance
from models.backtest.regime_selector import (
    RegimeSelector,
    RegimeSelectorConfig,
    build_regime_frame,
)
from models.backtest.regime_ranking import RegimeRankingEngine, RankingConfig


@dataclass
class BacktestConfig:
    date_col: str = "date"
    regime_col: str = "regime"
    prob_3m_col: str = "prob_3m"
    prob_6m_col: str = "prob_6m"

    transaction_cost_bps: float = 5.0
    periods_per_year: int = 12
    signal_lag_periods: int = 1
    risk_free_rate: float = 0.0

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
            portfolio_weights, portfolio_returns
        )

        gross_returns = (portfolio_weights * portfolio_returns).sum(axis=1)

        turnover = portfolio_weights.diff().abs().sum(axis=1).fillna(
            portfolio_weights.abs().sum(axis=1)
        )

        tc = turnover * (self.config.transaction_cost_bps / 10000.0)
        net_returns = gross_returns - tc

        equity_curve = (1.0 + net_returns).cumprod()

        result_frame = pd.DataFrame(
            {
                "portfolio_net_return": net_returns,
                "equity_curve": equity_curve,
            },
            index=aligned_returns.index,
        )

        metrics = summarize_performance(
            returns=net_returns,
            turnover=turnover,
            periods_per_year=self.config.periods_per_year,
            risk_free_rate=self.config.risk_free_rate,
        )

        return {
            "timeseries": result_frame.reset_index(),
            "weights": portfolio_weights.reset_index(),
            "metrics": metrics,
        }

    def _prepare_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        else:
            df.index = pd.to_datetime(df.index)
        return df.sort_index()

    def _prepare_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        else:
            df.index = pd.to_datetime(df.index)
        return df.sort_index().astype(float)

    def _build_weight_frame(self, signals: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:

        if self.config.use_regime_ranking:
            print(">>> USING REGIME RANKING <<<")
            regime_df = build_regime_frame(signals)
            return self.ranking_engine.build_top_n_weights(regime_df, returns)

        return pd.DataFrame(0.0, index=returns.index, columns=returns.columns)

    def _apply_vol_targeting(self, weights, returns):
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