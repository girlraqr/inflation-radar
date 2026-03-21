from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from models.backtest.regime_ranking import RegimeRankingEngine, RankingConfig


# --------------------------------------------------
# STATIC REGIME ALLOCATION
# --------------------------------------------------


@dataclass(frozen=True)
class RegimeAllocation:
    regime_to_weights: Dict[str, Dict[str, float]]

    def get_weights(self, regime: str) -> Dict[str, float]:
        return self.regime_to_weights.get(regime, {})


DEFAULT_REGIME_ALLOCATION = RegimeAllocation(
    regime_to_weights={
        "short_term_reflation": {
            "tips": 0.30,
            "commodities": 0.20,
            "energy_equities": 0.20,
            "financials": 0.15,
            "duration_long": -0.15,
        },
        "neutral": {
            "equities_broad": 0.25,
            "duration_intermediate": 0.25,
            "tips": 0.20,
            "gold": 0.10,
            "cash": 0.20,
        },
    }
)


# --------------------------------------------------
# STATIC WEIGHTS BUILDER
# --------------------------------------------------


def build_static_regime_weights(
    regime_df: pd.DataFrame,
    regime_allocations: RegimeAllocation,
    assets: List[str],
) -> pd.DataFrame:

    weights = pd.DataFrame(0.0, index=regime_df.index, columns=assets)

    for dt, row in regime_df.iterrows():
        regime = str(row["regime"])
        alloc = regime_allocations.get_weights(regime)

        total = sum(abs(v) for v in alloc.values())
        if total == 0:
            continue

        for asset, w in alloc.items():
            if asset in weights.columns:
                weights.at[dt, asset] = w / total

    return weights


# --------------------------------------------------
# RANKING-BASED WEIGHTS (PHASE C 🔥)
# --------------------------------------------------


def build_ranked_regime_weights(
    regime_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    top_n: int = 3,
    lookback_months: int = 24,
    min_history: int = 6,
) -> pd.DataFrame:

    engine = RegimeRankingEngine(
        RankingConfig(
            top_n=top_n,
            lookback_months=lookback_months,
            min_history=min_history,
        )
    )

    weights = engine.build_top_n_weights(
        regime_df=regime_df,
        returns_df=returns_df,
    )

    return weights