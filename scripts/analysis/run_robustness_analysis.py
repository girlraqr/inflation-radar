import pandas as pd

from models.backtest.backtest_engine import BacktestEngine, BacktestConfig


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

signals = pd.read_csv("storage/cache/signal_history.csv", parse_dates=["date"])
returns = pd.read_csv("storage/cache/asset_returns.csv", parse_dates=["date"])

# 🔥 TIMEZONE FIX
signals["date"] = signals["date"].dt.tz_localize(None)
returns["date"] = returns["date"].dt.tz_localize(None)

# 🔥 MERGE (wichtig!)
df = signals.merge(returns, on="date").sort_values("date").reset_index(drop=True)


# --------------------------------------------------
# ENGINE HELPER
# --------------------------------------------------

def run_engine(df_subset, transaction_cost_bps=5, slippage_bps=1):
    engine = BacktestEngine(
        config=BacktestConfig(
            smoothing_alpha=0.30,
            gamma=1.35,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
            include_costs=True,
        )
    )

    signals_df = df_subset[signals.columns]
    returns_df = df_subset[returns.columns]

    return engine.run(signals_df, returns_df)


# --------------------------------------------------
# 1. WALK-FORWARD
# --------------------------------------------------

def run_walk_forward(df):

    results = []
    years = sorted(df["date"].dt.year.unique())

    for i in range(5, len(years) - 1):
        test_year = years[i]

        df_test = df[df["date"].dt.year == test_year]

        result = run_engine(df_test)

        results.append({
            "year": test_year,
            "sharpe": result["metrics"]["sharpe"],
            "return": result["metrics"]["annual_return"],
            "drawdown": result["metrics"]["max_drawdown"],
        })

    return pd.DataFrame(results)


# --------------------------------------------------
# 2. SUBPERIODS
# --------------------------------------------------

def run_subperiods(df):

    periods = [
        ("2011-01-01", "2015-12-31"),
        ("2016-01-01", "2020-12-31"),
        ("2021-01-01", "2025-12-31"),
    ]

    results = []

    for start, end in periods:
        df_sub = df[(df["date"] >= start) & (df["date"] <= end)]

        result = run_engine(df_sub)

        results.append({
            "period": f"{start} → {end}",
            "sharpe": result["metrics"]["sharpe"],
            "return": result["metrics"]["annual_return"],
        })

    return pd.DataFrame(results)


# --------------------------------------------------
# 3. COST SENSITIVITY
# --------------------------------------------------

def run_cost_sensitivity(df):

    costs = [5, 10, 20, 50]
    results = []

    for cost in costs:
        result = run_engine(
            df,
            transaction_cost_bps=cost,
            slippage_bps=cost / 5,
        )

        results.append({
            "cost_bps": cost,
            "sharpe": result["metrics"]["sharpe"],
            "return": result["metrics"]["annual_return"],
        })

    return pd.DataFrame(results)


# --------------------------------------------------
# 4. SIGNAL EDGE (ROBUST FIX)
# --------------------------------------------------

def analyze_signal_edge(df):

    # 🔥 bekannte Nicht-Return Spalten ausschließen
    exclude_cols = ["date", "prob_3m", "prob_6m", "regime"]

    return_cols = [col for col in df.columns if col not in exclude_cols]

    # Falls keine Returns gefunden werden → abbrechen
    if len(return_cols) == 0:
        print("⚠️ Keine Return-Spalten gefunden")
        return

    # 🔥 Durchschnittlicher zukünftiger Return
    df["future_return"] = df[return_cols].mean(axis=1).shift(-1)

    # 🔥 Correlation berechnen
    corr = df["prob_3m"].corr(df["future_return"])

    print("\nSignal Correlation (prob_3m → future avg return):", round(corr, 4))


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    print("\n==============================")
    print(" WALK FORWARD")
    print("==============================")
    print(run_walk_forward(df))

    print("\n==============================")
    print(" SUBPERIODS")
    print("==============================")
    print(run_subperiods(df))

    print("\n==============================")
    print(" COST SENSITIVITY")
    print("==============================")
    print(run_cost_sensitivity(df))

    print("\n==============================")
    print(" SIGNAL EDGE")
    print("==============================")
    analyze_signal_edge(df)