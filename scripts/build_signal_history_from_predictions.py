from __future__ import annotations

import pandas as pd

from models.signals.inflation_signal_engine import InflationSignalEngine


def main():
    print("Building signal history from predictions...")

    df = pd.read_csv("storage/cache/predictions.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    engine = InflationSignalEngine()

    rows = []

    for _, row in df.iterrows():
        prob_3m = row["prob_3m"]
        prob_6m = row["prob_6m"]

        signal = engine.generate_signals(
            prob_3m=prob_3m,
            prob_6m=prob_6m,
        )

        rows.append(
            {
                "date": row["date"],
                "prob_3m": prob_3m,
                "prob_6m": prob_6m,
                "regime": signal["regime"],
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv("storage/cache/signal_history.csv", index=False)

    print("✅ signal_history.csv erstellt!")


if __name__ == "__main__":
    main()