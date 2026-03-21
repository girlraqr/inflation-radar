from __future__ import annotations

import pandas as pd

from models.ml.feature_engineering import FeatureEngineering
from models.ml.inflation_model import InflationModel


def main():
    print("Generating predictions...")

    # === Dataset laden ===
    df = pd.read_csv("storage/cache/ml_dataset.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.set_index("date")  # 🔥 KRITISCH

    results = []

    MIN_HISTORY = 60  # warmup für Features

    # === Modelle laden (KEIN retraining!) ===
    model_3m = InflationModel(horizon="3m")
    model_6m = InflationModel(horizon="6m")

    model_3m.load_model("storage/cache/inflation_model_3m.joblib")
    model_6m.load_model("storage/cache/inflation_model_6m.joblib")

    # === Loop über Zeit ===
    for i in range(MIN_HISTORY, len(df)):
        df_slice = df.iloc[: i + 1].copy()

        # === Feature Engineering ===
        fe = FeatureEngineering(df_slice)
        features = fe.create_features()

        if features.empty:
            continue

        latest = features.iloc[-1:]

        # === Predictions ===
        prob_3m = float(model_3m.predict_proba(latest)[0])
        prob_6m = float(model_6m.predict_proba(latest)[0])

        results.append(
            {
                "date": latest.index[0],  # sauberer als column
                "prob_3m": prob_3m,
                "prob_6m": prob_6m,
            }
        )

        if i % 25 == 0:
            print(f"Progress: {i}/{len(df)}")

    out = pd.DataFrame(results)
    out.to_csv("storage/cache/predictions.csv", index=False)

    print("✅ predictions.csv erstellt!")


if __name__ == "__main__":
    main()