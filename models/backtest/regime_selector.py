from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class RegimeSelectorConfig:
    min_conviction: float = 0.25
    allowed_regimes: tuple[str, ...] = (
        "short_term_reflation",
        "neutral",
    )


class RegimeSelector:
    def __init__(self, config: RegimeSelectorConfig | None = None) -> None:
        self.config = config or RegimeSelectorConfig()

    def should_trade(self, regime: str, conviction: float) -> bool:
        if regime not in self.config.allowed_regimes:
            return False

        if conviction < self.config.min_conviction:
            return False

        return True


def build_regime_frame(predictions: pd.DataFrame) -> pd.DataFrame:
    """
    Convert predictions dataframe into standardized regime dataframe.

    Output:
    index = datetime
    column = ['regime']
    """

    df = predictions.copy()

    # --- Handle date ---
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # --- Case 1: already has regime ---
    if "regime" in df.columns:
        out = df[["regime"]].copy()
        out["regime"] = out["regime"].astype(str)
        return out

    # --- Case 2: probability columns ---
    prob_cols = [c for c in df.columns if c.startswith("prob_")]
    if prob_cols:
        out = pd.DataFrame(index=df.index)
        out["regime"] = df[prob_cols].idxmax(axis=1)
        out["regime"] = out["regime"].str.replace("prob_", "", regex=False)
        return out

    # --- Case 3: fallback signal ---
    for col in ["signal", "inflation_signal", "direction"]:
        if col in df.columns:
            out = pd.DataFrame(index=df.index)
            out["regime"] = df[col].astype(str)
            return out

    raise ValueError("No regime information found in predictions")