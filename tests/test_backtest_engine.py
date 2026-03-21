from __future__ import annotations

import pandas as pd

from models.backtest.backtest_engine import BacktestEngine, BacktestConfig
from models.backtest.allocation import RegimeAllocation


def test_backtest_engine_no_lookahead_and_basic_metrics():
    signals = pd.DataFrame(
        {
            "date": ["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"],
            "regime": [
                "short_term_reflation",
                "disinflation",
                "short_term_reflation",
                "disinflation",
            ],
        }
    )

    returns = pd.DataFrame(
        {
            "date": ["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"],
            "asset_a": [0.01, 0.02, -0.01, 0.03],
            "asset_b": [-0.01, 0.00, 0.02, -0.01],
        }
    )

    allocation = RegimeAllocation(
        regime_to_weights={
            "short_term_reflation": {"asset_a": 1.0},
            "disinflation": {"asset_b": 1.0},
        }
    )

    engine = BacktestEngine(
        allocation=allocation,
        config=BacktestConfig(
            date_col="date",
            regime_col="regime",
            signal_lag_periods=1,
            transaction_cost_bps=0.0,
        ),
    )

    result = engine.run(signals_df=signals, returns_df=returns)
    ts = result["timeseries"]

    # Wegen signal_lag_periods=1:
    # Feb nutzt Jan-Signal -> asset_a -> 0.02
    # Mar nutzt Feb-Signal -> asset_b -> 0.02
    # Apr nutzt Mar-Signal -> asset_a -> 0.03
    realized = ts["portfolio_net_return"].round(6).tolist()

    assert realized == [0.02, 0.02, 0.03]
    assert result["metrics"]["total_return"] > 0
    assert result["metrics"]["max_drawdown"] <= 0