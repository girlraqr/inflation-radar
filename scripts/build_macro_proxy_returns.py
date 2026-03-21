from __future__ import annotations

import pandas as pd

from models.ml.feature_engineering import FeatureEngineering


def main():
    print("Building asset returns...")

    df = pd.read_csv("storage/cache/ml_dataset.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.set_index("date")

    # 🔥 Feature Engineering nutzen!
    fe = FeatureEngineering(df)
    features = fe.create_features()

    returns = pd.DataFrame(index=features.index)

    # --------------------------------------------------
    # Bonds (Duration proxy)
    # --------------------------------------------------
    returns["duration_10y"] = -features["ust_10y"].diff()

    # --------------------------------------------------
    # Inflation (TIPS proxy)
    # --------------------------------------------------
    returns["tips"] = features["cpi"].pct_change()

    # --------------------------------------------------
    # Commodities
    # --------------------------------------------------
    returns["commodities"] = features["wti_oil"].pct_change()

    # --------------------------------------------------
    # Dollar
    # --------------------------------------------------
    returns["usd"] = features["broad_dollar_index"].pct_change()

    # --------------------------------------------------
    # Gold (via real rates)
    # --------------------------------------------------
    returns["gold"] = -features["real_rate_ff"].diff()

    # --------------------------------------------------
    # Equities
    # --------------------------------------------------
    returns["equities_broad"] = features["gdp"].pct_change()
    returns["equities_value"] = features["industrial_production"].pct_change()
    returns["cyclical_equities"] = features["retail_sales"].pct_change()

    # --------------------------------------------------
    # Quality proxy
    # --------------------------------------------------
    returns["quality_equities"] = -features["credit_spread_baa_aaa"].diff()

    # --------------------------------------------------
    # Cash
    # --------------------------------------------------
    returns["cash"] = features["fed_funds"] / 100 / 12

    # --------------------------------------------------
    # CLEAN
    # --------------------------------------------------
    returns = returns.replace([float("inf"), float("-inf")], pd.NA)
    returns = returns.dropna()

    returns.to_csv("storage/cache/asset_returns.csv")

    print("✅ asset_returns.csv erstellt!")
    print(returns.head())


if __name__ == "__main__":
    main()