from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from models.backtest.regime_probability_mapper import (
    BaselineRegimeMapperConfig,
    BaselineRegimeProbabilityMapper,
)
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
# HELPERS
# --------------------------------------------------


def _normalize_weights(weight_map: Dict[str, float]) -> Dict[str, float]:
    total = sum(abs(v) for v in weight_map.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in weight_map.items()}


def _normalize_probabilities(prob_map: Dict[str, float]) -> Dict[str, float]:
    total = sum(float(v) for v in prob_map.values())
    if total <= 0:
        n = len(prob_map)
        if n == 0:
            return {}
        return {k: 1.0 / n for k in prob_map}
    return {k: float(v) / total for k, v in prob_map.items()}


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
# PROBABILISTIC REGIME WEIGHTS (PHASE 10.3 BASELINE)
# --------------------------------------------------


def build_probabilistic_regime_weights(
    regime_df: pd.DataFrame,
    regime_allocations: RegimeAllocation,
    assets: List[str],
    smoothing_alpha: float = 0.25,
    mapper_temperature: float = 0.70,
    mapper: Optional[BaselineRegimeProbabilityMapper] = None,
) -> pd.DataFrame:
    """
    Phase 10.3 baseline mapper:
    - mappt row-basierte Features auf regime probabilities
    - glättet diese Wahrscheinlichkeiten zeitlich
    - baut daraus weiche Asset-Gewichte

    Erwartete Input-Spalten in regime_df:
    - regime
    - prob_3m
    - prob_6m
    """
 # 🔥 DEBUG PRINT – HIER IST DIE RICHTIGE STELLE
    print(">>> SMOOTHING ALPHA USED:", smoothing_alpha)
    weights = pd.DataFrame(0.0, index=regime_df.index, columns=assets)

    all_regimes = list(regime_allocations.regime_to_weights.keys())
    if not all_regimes:
        return weights

    alpha = max(0.0, min(1.0, float(smoothing_alpha)))

    regime_mapper = mapper or BaselineRegimeProbabilityMapper(
        BaselineRegimeMapperConfig(temperature=mapper_temperature)
    )

    prev_probs: Dict[str, float] = {
        regime: 1.0 / len(all_regimes)
        for regime in all_regimes
    }

    for dt, row in regime_df.iterrows():
        raw_probs = regime_mapper.map_row_to_probabilities(
            row=row,
            allowed_regimes=all_regimes,
        )

        smoothed_probs: Dict[str, float] = {}
        for regime in all_regimes:
            current_prob = float(raw_probs.get(regime, 0.0))
            prev_prob = float(prev_probs.get(regime, 0.0))
            smoothed_probs[regime] = alpha * current_prob + (1.0 - alpha) * prev_prob

        smoothed_probs = _normalize_probabilities(smoothed_probs)
        prev_probs = smoothed_probs.copy()

        combined_weights: Dict[str, float] = {}

        for regime, prob in smoothed_probs.items():
            alloc = regime_allocations.get_weights(regime)
            if not alloc:
                continue

            normalized_alloc = _normalize_weights(alloc)

            for asset, weight in normalized_alloc.items():
                combined_weights[asset] = combined_weights.get(asset, 0.0) + (prob * weight)

        if not combined_weights:
            continue

        for asset, weight in combined_weights.items():
            if asset in weights.columns:
                weights.at[dt, asset] = weight

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