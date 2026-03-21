from __future__ import annotations

import pandas as pd

from models.backtest.backtest_engine import BacktestEngine, BacktestConfig
from models.backtest.allocation import DEFAULT_REGIME_ALLOCATION


class BacktestService:
    def __init__(self) -> None:
        self.engine = BacktestEngine(
            allocation=DEFAULT_REGIME_ALLOCATION,
            config=BacktestConfig(
                date_col="date",
                regime_col="regime",
                prob_3m_col="prob_3m",
                prob_6m_col="prob_6m",
                transaction_cost_bps=5.0,
                periods_per_year=12,
                signal_lag_periods=1,
                risk_free_rate=0.0,

                # 🔥 TEST SETUP (Alpha Isolation)
                conviction_method="power",
                conviction_floor=0.35,

                # optional (für spätere Tests)
                conviction_exponent=1.3,
                logistic_k=10.0,
                logistic_threshold=0.3,
            ),
        )

    def run_backtest(
        self,
        signals_df: pd.DataFrame,
        returns_df: pd.DataFrame,
    ) -> dict:
        return self.engine.run(signals_df=signals_df, returns_df=returns_df)