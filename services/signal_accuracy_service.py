from __future__ import annotations

from typing import Dict, Any, List
import pandas as pd

from services.performance_engine_service import PerformanceEngineService


class SignalAccuracyService:

    def __init__(self) -> None:
        self.performance_service = PerformanceEngineService()

    # ---------------------------------------------------
    # MAIN
    # ---------------------------------------------------

    def build_signal_accuracy(self, user_id: int) -> Dict[str, Any]:

        result = self.performance_service.build_performance(user_id=user_id)

        history = result.history

        if not history or len(history) < 2:
            raise ValueError("Not enough history for accuracy calculation")

        # ---------------------------------------------------
        # LOAD SIGNAL HISTORY
        # ---------------------------------------------------

        df_signals = pd.read_csv("storage/cache/signal_history.csv")
        df_signals["date"] = pd.to_datetime(df_signals["date"]).dt.tz_localize(None)

        # ---------------------------------------------------
        # BUILD DATASET
        # ---------------------------------------------------

        records = []

        for i in range(len(history) - 1):

            current = history[i]
            nxt = history[i + 1]

            date = pd.to_datetime(current["date"]).tz_localize(None)

            # Signal zum Zeitpunkt t
            signal_row = df_signals[df_signals["date"] <= date]

            if signal_row.empty:
                continue

            signal_row = signal_row.iloc[-1]

            regime = str(signal_row["regime"]).lower()

            forward_return = nxt["period_return"]

            records.append(
                {
                    "date": date,
                    "regime": regime,
                    "forward_return": forward_return,
                    "hit": 1 if forward_return > 0 else 0,
                }
            )

        df = pd.DataFrame(records)

        if df.empty:
            raise ValueError("No accuracy data built")

        # ---------------------------------------------------
        # AGGREGATION
        # ---------------------------------------------------

        summary: Dict[str, Any] = {}

        for regime, group in df.groupby("regime"):

            observations = len(group)

            hit_rate = group["hit"].mean()
            avg_return = group["forward_return"].mean()
            volatility = group["forward_return"].std()

            summary[regime] = {
                "observations": observations,
                "hit_rate": round(float(hit_rate), 4),
                "avg_return": round(float(avg_return), 6),
                "volatility": round(float(volatility), 6) if pd.notna(volatility) else 0.0,
            }

        # ---------------------------------------------------
        # GLOBAL STATS
        # ---------------------------------------------------

        overall = {
            "observations": len(df),
            "hit_rate": round(float(df["hit"].mean()), 4),
            "avg_return": round(float(df["forward_return"].mean()), 6),
        }

        return {
            "by_regime": summary,
            "overall": overall,
        }