# ===== VERSION C: HYBRID =====
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


@dataclass
class RankingConfig:
    lookback_months: int = 24
    min_history: int = 6
    top_n: int = 4

    rebalance_frequency_months: int = 15
    selection_buffer: int = 6

    use_score_weighting: bool = True
    smoothing_alpha: float = 0.10


class RegimeRankingEngine:
    def __init__(self, config: Optional[RankingConfig] = None):
        self.config = config or RankingConfig()

    def rank_for_date(self, dt, regime, regime_df, returns_df):
        hist = returns_df.loc[returns_df.index < dt].tail(24)
        if hist.empty:
            return pd.DataFrame()
        return hist.mean().sort_values(ascending=False).to_frame("score")

    def build_top_n_weights(self, regime_df, returns_df):
        dates = returns_df.index
        assets = returns_df.columns
        weights = pd.DataFrame(0.0, index=dates, columns=assets)

        prev = pd.Series(0.0, index=assets)

        for i, dt in enumerate(dates):
            ranked = returns_df.loc[:dt].tail(24).mean().sort_values(ascending=False)

            selected = ranked.index[:self.config.top_n]

            scores = ranked.loc[selected]
            scores = scores / scores.sum()

            target = pd.Series(0.0, index=assets)
            target[selected] = scores

            if i == 0:
                smoothed = target
            else:
                smoothed = (1 - self.config.smoothing_alpha) * prev + self.config.smoothing_alpha * target

            weights.loc[dt] = smoothed
            prev = smoothed

        return weights.fillna(0.0)