from __future__ import annotations

import pandas as pd


# ---------------------------------------------------
# REGIME CLASSIFICATION (IMPROVED)
# ---------------------------------------------------

def classify_regime(prob_3m: float, prob_6m: float) -> str:

    if pd.isna(prob_3m) or pd.isna(prob_6m):
        return "neutral"

    # 🔥 bessere Differenzierung
    if prob_3m > 0.6 and prob_6m > 0.6:
        return "reflation"

    if prob_3m > 0.6 and prob_6m <= 0.5:
        return "short_term_reflation"

    if prob_3m < 0.4 and prob_6m < 0.4:
        return "disinflation_strong"

    if prob_3m < 0.45 and prob_6m < 0.5:
        return "short_term_disinflation"

    if 0.4 <= prob_3m <= 0.6 and prob_6m > 0.5:
        return "inflation_bottoming"

    return "neutral"


# ---------------------------------------------------
# MAIN BUILDER
# ---------------------------------------------------

def build_signal_history():

    print("=== BUILD SIGNAL HISTORY FROM PREDICTIONS ===")

    # ---------------------------------------------------
    # LOAD PREDICTIONS
    # ---------------------------------------------------

    path = "storage/cache/predictions.csv"

    df = pd.read_csv(path)

    if "date" not in df.columns:
        raise ValueError("❌ 'date' column missing in predictions.csv")

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date")

    # ---------------------------------------------------
    # DEBUG (🔥 WICHTIG)
    # ---------------------------------------------------

    print("\n[DEBUG] Predictions range:")
    print(df["date"].min(), "→", df["date"].max())

    print("\n[DEBUG] Sample:")
    print(df.tail())

    # ---------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------

    required_cols = ["prob_3m", "prob_6m"]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"❌ Missing column: {col}")

    # ---------------------------------------------------
    # BUILD SIGNAL HISTORY
    # ---------------------------------------------------

    records = []

    for _, row in df.iterrows():

        prob_3m = row["prob_3m"]
        prob_6m = row["prob_6m"]

        regime = classify_regime(prob_3m, prob_6m)

        records.append(
            {
                "date": row["date"],
                "prob_3m": prob_3m,
                "prob_6m": prob_6m,
                "regime": regime,
            }
        )

    result = pd.DataFrame(records)

    # ---------------------------------------------------
    # CLEAN
    # ---------------------------------------------------

    result = result.dropna(subset=["date"])

    result = result.sort_values("date")

    # ---------------------------------------------------
    # DEBUG OUTPUT
    # ---------------------------------------------------

    print("\n[DEBUG] Signal history range:")
    print(result["date"].min(), "→", result["date"].max())

    print("\n[DEBUG] Regime distribution:")
    print(result["regime"].value_counts())

    print("\n[DEBUG] Last rows:")
    print(result.tail())

    # ---------------------------------------------------
    # SAVE
    # ---------------------------------------------------

    out_path = "storage/cache/signal_history.csv"
    result.to_csv(out_path, index=False)

    print(f"\n✅ Saved to {out_path}")


# ---------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------

if __name__ == "__main__":
    build_signal_history()