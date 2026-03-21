from __future__ import annotations

import pandas as pd

from models.backtest.backtest_engine import BacktestEngine, BacktestConfig


def load_with_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures dataframe has datetime index.
    Works whether 'date' is column or already index.
    """

    df = df.copy()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    else:
        # assume index is already date
        df.index = pd.to_datetime(df.index)

    return df.sort_index()


def main():
    print("=== START PHASE C BACKTEST ===")

    # --------------------------------------------------
    # LOAD
    # --------------------------------------------------

    predictions = pd.read_csv("storage/cache/predictions.csv")
    asset_returns = pd.read_csv("storage/cache/asset_returns.csv")

    print("Raw shapes:")
    print("predictions:", predictions.shape)
    print("returns:", asset_returns.shape)

    # --------------------------------------------------
    # FIX DATE HANDLING
    # --------------------------------------------------

    predictions = load_with_date(predictions)
    asset_returns = load_with_date(asset_returns)

    print("\nAfter date handling:")
    print("predictions index:", predictions.index[:3])
    print("returns index:", asset_returns.index[:3])

    # --------------------------------------------------
    # CONFIG
    # --------------------------------------------------

    config = BacktestConfig(
        use_regime_ranking=True,  # 🔥 Phase C aktiv
    )

    engine = BacktestEngine(config=config)

    # --------------------------------------------------
    # RUN
    # --------------------------------------------------

    result = engine.run(
        signals_df=predictions,
        returns_df=asset_returns,
    )

    timeseries = result["timeseries"]
    weights = result["weights"]
    metrics = result["metrics"]

    print("\n=== BACKTEST DONE ===")

    print("\nMetrics:")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    print("\nTimeseries head:")
    print(timeseries.head())

    print("\nWeights head:")
    print(weights.head())

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    timeseries.to_csv("storage/cache/backtest_timeseries_phase_c.csv", index=False)
    weights.to_csv("storage/cache/backtest_weights_phase_c.csv", index=False)

    print("\nSaved:")
    print(" - storage/cache/backtest_timeseries_phase_c.csv")
    print(" - storage/cache/backtest_weights_phase_c.csv")


if __name__ == "__main__":
    main()