from __future__ import annotations

import math
from typing import Dict, Any


PORTFOLIO_REGIMES = [
    "REFLATION",
    "DEFLATION",
    "STAGFLATION",
    "GOLDILOCKS",
    "NEUTRAL",
]


RAW_TO_PORTFOLIO_REGIME = {
    "reflation": "REFLATION",
    "short_term_reflation": "REFLATION",
    "disinflation_strong": "DEFLATION",
    "short_term_disinflation": "STAGFLATION",
    "inflation_bottoming": "GOLDILOCKS",
    "neutral": "NEUTRAL",
}


class ProbabilisticRegimeService:
    """
    Phase 10.1:
    - deterministic regime → probabilistic distribution
    - no lookahead
    - simple but robust baseline model
    """

    def __init__(
        self,
        temperature: float = 1.0,
        base_regime_boost: float = 2.0,
        other_regime_floor: float = 0.5,
    ) -> None:
        self.temperature = temperature
        self.base_regime_boost = base_regime_boost
        self.other_regime_floor = other_regime_floor

    # =========================================================
    # PUBLIC API
    # =========================================================

    def compute_regime_probabilities(
        self,
        raw_regime: str,
    ) -> Dict[str, Any]:

        base_regime = self._map_raw_to_portfolio_regime(raw_regime)

        raw_scores = self._build_raw_scores(base_regime)
        probabilities = self._softmax(raw_scores)

        return {
            "base_regime": base_regime,
            "raw_scores": raw_scores,
            "probabilities": probabilities,
        }

    # =========================================================
    # CORE LOGIC
    # =========================================================

    def _map_raw_to_portfolio_regime(self, raw_regime: str) -> str:
        if not raw_regime:
            return "NEUTRAL"

        return RAW_TO_PORTFOLIO_REGIME.get(raw_regime.lower(), "NEUTRAL")

    def _build_raw_scores(self, base_regime: str) -> Dict[str, float]:
        scores: Dict[str, float] = {}

        for regime in PORTFOLIO_REGIMES:
            if regime == base_regime:
                scores[regime] = float(self.base_regime_boost)
            else:
                scores[regime] = float(self.other_regime_floor)

        return scores

    def _softmax(self, scores: Dict[str, float]) -> Dict[str, float]:
        if not scores:
            return {}

        scaled = {k: v / self.temperature for k, v in scores.items()}
        max_val = max(scaled.values())

        exp_values = {k: math.exp(v - max_val) for k, v in scaled.items()}
        total = sum(exp_values.values())

        if total <= 0:
            n = len(scores)
            return {k: 1.0 / n for k in scores}

        return {k: v / total for k, v in exp_values.items()}