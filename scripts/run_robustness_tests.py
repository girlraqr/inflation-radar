import pandas as pd
import itertools

from models.backtest.backtest_engine import BacktestEngine, BacktestConfig


# =========================================================
# CONFIG
# =========================================================

ALPHA_GRID = [0.20, 0.25, 0.30]
GAMMA_GRID = [1.2, 1.35, 1.5]
COST_GRID = [1.0, 5.0, 10.0]

OUTPUT_FILE = "storage/cache/robustness_results.csv"


# =========================================================
# LOAD DATA
# =========================================================

def load_data():
    signals = pd.read_csv("storage/cache/predictions.csv")
    returns = pd.read_csv("storage/cache/asset_returns.csv")
    return signals, returns


# =========================================================
# RUN SINGLE TEST
# =========================================================

def run_single_test(signals, returns, alpha, gamma, cost_bps):

    config = BacktestConfig(
        smoothing_alpha=alpha,
        transaction_cost_bps=cost_bps,
        slippage_bps=0.0,
        use_regime_ranking=False,
    )

    # 🔥 Gamma override (temporary)
    import models.backtest.allocation as allocation
    allocation.GAMMA = gamma

    engine = BacktestEngine(config=config)

    result = engine.run(signals, returns)
    metrics = result["metrics"]

    return {
        "alpha": alpha,
        "gamma": gamma,
        "cost_bps": cost_bps,
        "sharpe": metrics.get("sharpe"),
        "annual_return": metrics.get("annual_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "turnover": metrics.get("annual_turnover"),
        "cost_drag": metrics.get("cost_drag", 0.0),
    }


# =========================================================
# MAIN LOOP
# =========================================================

def run_grid():
    signals, returns = load_data()

    results = []

    combinations = list(itertools.product(ALPHA_GRID, GAMMA_GRID, COST_GRID))

    print(f"Running {len(combinations)} combinations...")

    for i, (alpha, gamma, cost) in enumerate(combinations):
        print(f"[{i+1}/{len(combinations)}] alpha={alpha}, gamma={gamma}, cost={cost}")

        try:
            res = run_single_test(signals, returns, alpha, gamma, cost)
            if res["sharpe"] is not None:
                results.append(res)
        except Exception as e:
            print("ERROR:", e)

    df = pd.DataFrame(results)

    if not df.empty:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSaved results to {OUTPUT_FILE}")
    else:
        print("\n⚠️ No valid results generated")

    return df


# =========================================================
# ANALYSIS
# =========================================================

def summarize(df: pd.DataFrame):

    if df.empty:
        print("No data to summarize")
        return

    print("\n=== TOP SHARPE ===")
    print(df.sort_values("sharpe", ascending=False).head(10))

    print("\n=== MOST STABLE ===")
    df["score"] = df["sharpe"] - abs(df["max_drawdown"]) * 0.5
    print(df.sort_values("score", ascending=False).head(10))

    print("\n=== COST SENSITIVITY ===")
    print(df.groupby("cost_bps")["sharpe"].mean())


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    df = run_grid()
    summarize(df)