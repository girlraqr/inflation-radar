import pandas as pd
from models.backtest.backtest_engine import BacktestEngine, BacktestConfig


def run_walk_forward(signals_df, returns_df):

    results = []

    years = sorted(signals_df["date"].dt.year.unique())

    for i in range(5, len(years) - 1):
        train_years = years[:i]
        test_year = years[i]

        train_mask = signals_df["date"].dt.year.isin(train_years)
        test_mask = signals_df["date"].dt.year == test_year

        signals_test = signals_df[test_mask]
        returns_test = returns_df[test_mask]

        engine = BacktestEngine(
            config=BacktestConfig(
                smoothing_alpha=0.30,
                gamma=1.35,
                transaction_cost_bps=5,
                slippage_bps=1,
                include_costs=True,
            )
        )

        result = engine.run(signals_test, returns_test)

        results.append({
            "year": test_year,
            "sharpe": result["metrics"]["sharpe"],
            "return": result["metrics"]["annual_return"],
            "drawdown": result["metrics"]["max_drawdown"],
        })

    return pd.DataFrame(results)


if __name__ == "__main__":
    signals = pd.read_csv("storage/cache/signal_history.csv", parse_dates=["date"])
    returns = pd.read_csv("storage/cache/asset_returns.csv", parse_dates=["date"])

    df = run_walk_forward(signals, returns)
    print(df)