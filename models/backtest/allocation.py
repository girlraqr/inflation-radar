from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from models.backtest.regime_probability_mapper import (
    MultiRegimeMapperConfig,
    MultiRegimeProbabilityMapper,
)
from models.backtest.regime_ranking import RegimeRankingEngine, RankingConfig
from models.backtest.sharpe_booster import (
    SharpeBoosterConfig,
    apply_sharpe_booster,
)


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
        "reflation": {
            "tips": 0.30,
            "commodities": 0.25,
            "energy_equities": 0.20,
            "financials": 0.15,
            "duration_long": -0.10,
        },
        "short_term_reflation": {
            "tips": 0.25,
            "commodities": 0.20,
            "energy_equities": 0.15,
            "financials": 0.10,
            "duration_long": -0.10,
            "cash": 0.20,
        },
        "disinflation": {
            "duration_long": 0.40,
            "equities_broad": 0.25,
            "gold": 0.10,
            "cash": 0.25,
        },
        "short_term_disinflation": {
            "duration_intermediate": 0.30,
            "equities_broad": 0.20,
            "gold": 0.10,
            "cash": 0.40,
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
        return {k: 1.0 / n for k in prob_map}
    return {k: float(v) / total for k, v in prob_map.items()}


# --------------------------------------------------
# PROBABILISTIC REGIME WEIGHTS (CONFIG-DRIVEN)
# --------------------------------------------------


def build_probabilistic_regime_weights(
    regime_df: pd.DataFrame,
    regime_allocations: RegimeAllocation,
    assets: List[str],
    smoothing_alpha: float = 0.25,
    mapper_temperature: float = 0.70,
    mapper: Optional[MultiRegimeProbabilityMapper] = None,
    config=None,
) -> pd.DataFrame:

    print(">>> SMOOTHING ALPHA USED:", smoothing_alpha)

    weights = pd.DataFrame(0.0, index=regime_df.index, columns=assets)

    all_regimes = list(regime_allocations.regime_to_weights.keys())
    alpha = max(0.0, min(1.0, float(smoothing_alpha)))

    regime_mapper = mapper or MultiRegimeProbabilityMapper(
        MultiRegimeMapperConfig(temperature=mapper_temperature)
    )

    prev_probs = {r: 1.0 / len(all_regimes) for r in all_regimes}
    INERTIA = 0.15

    if config is not None and hasattr(config, "gamma"):
        gamma = config.gamma
    else:
        gamma = 1.35

    # Phase 2 Booster
    booster_config = SharpeBoosterConfig(
        enabled=True,
        min_prob=0.50,
        max_prob=0.90,
        min_scale=0.00,
        mid_scale=1.00,
        max_scale=1.20,
        curve_power=1.35,
        use_prob_6m_confirmation=True,
        prob_6m_penalty_threshold=0.45,
        prob_6m_penalty_scale=0.92,
        use_horizon_disagreement_penalty=False,
        disagreement_threshold=0.20,
        disagreement_penalty_scale=0.80,
        use_uncertainty_penalty=True,
        uncertainty_floor=0.35,
        uncertainty_ceiling=0.75,
        uncertainty_min_scale=0.78,
        uncertainty_max_scale=1.05,
        residual_asset="cash",
        min_leverage=0.0,
        max_leverage=1.60,
    )

    for dt, row in regime_df.iterrows():
        raw_probs = regime_mapper.map_row_to_probabilities(
            row=row,
            allowed_regimes=all_regimes,
        )

        # -----------------------------
        # SMOOTHING + INERTIA
        # -----------------------------
        smoothed = {}
        for r in all_regimes:
            base = alpha * raw_probs.get(r, 0.0) + (1 - alpha) * prev_probs[r]
            smoothed[r] = base + prev_probs[r] * INERTIA

        smoothed = _normalize_probabilities(smoothed)

        # -----------------------------
        # GAMMA BLENDING
        # -----------------------------
        adjusted = {r: pow(p, gamma) for r, p in smoothed.items()}
        adjusted = _normalize_probabilities(adjusted)
        prev_probs = adjusted.copy()

        # -----------------------------
        # EXISTING CONFIDENCE SCALING
        # -----------------------------
        regime_confidence = max(adjusted.values())

        FLOOR, CEIL = 0.50, 0.85
        MIN_S, MAX_S = 0.85, 1.15

        c = max(FLOOR, min(CEIL, regime_confidence))
        norm = (c - FLOOR) / (CEIL - FLOOR)
        scale = MIN_S + norm * (MAX_S - MIN_S)

        # -----------------------------
        # WEIGHT AGGREGATION
        # -----------------------------
        combined: Dict[str, float] = {}

        for r, prob in adjusted.items():
            alloc = regime_allocations.get_weights(r)
            alloc = _normalize_weights(alloc)

            for a, w in alloc.items():
                combined[a] = combined.get(a, 0.0) + prob * w * scale

        # -----------------------------
        # PHASE 2 SHARPE BOOSTER
        # -----------------------------
        signal_row = {
            "prob_3m": row.get("prob_3m", 0.0),
            "prob_6m": row.get("prob_6m", 0.0),
            "regime_confidence": regime_confidence,
        }

        combined = apply_sharpe_booster(
            weights=combined,
            signal_row=signal_row,
            config=booster_config,
        )

        # -----------------------------
        # WRITE TO DF
        # -----------------------------
        for a, w in combined.items():
            if a in weights.columns:
                weights.at[dt, a] = w

    return weights


# --------------------------------------------------
# RANKING-BASED WEIGHTS
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