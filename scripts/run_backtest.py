from __future__ import annotations

import pandas as pd

from services.backtest_service import BacktestService


def main() -> None:
    signals_df = pd.read_csv("storage/cache/signal_history.csv")
    returns_df = pd.read_csv("storage/cache/asset_returns.csv")

    service = BacktestService()
    result = service.run_backtest(signals_df=signals_df, returns_df=returns_df)

    print("=== METRICS ===")
    for k, v in result["metrics"].items():
        print(f"{k}: {v}")

    if "regime_breakdown" in result:
        print("\n=== REGIME BREAKDOWN ===")
        for regime, stats in result["regime_breakdown"].items():
            print(regime, stats)

    result["timeseries"].to_csv("storage/cache/backtest_timeseries.csv", index=False)
    result["weights"].to_csv("storage/cache/backtest_weights.csv", index=False)


if __name__ == "__main__":
    main()