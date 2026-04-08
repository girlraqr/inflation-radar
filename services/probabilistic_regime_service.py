from __future__ import annotations

import math
from typing import Dict, List


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
    def __init__(self, temperature: float = 1.0):
        self.temperature = temperature

    # =========================================================
    # MAIN
    # =========================================================

    def compute_regime_probabilities(self, raw_regime: str) -> Dict[str, float]:
        base_regime = RAW_TO_PORTFOLIO_REGIME.get(raw_regime.lower(), "NEUTRAL")

        raw_scores = self._build_raw_scores(base_regime)
        probabilities = self._softmax(raw_scores)

        return {
            "base_regime": base_regime,
            "raw_scores": raw_scores,
            "probabilities": probabilities,
        }

    # =========================================================
    # RAW SCORE MODEL (Phase 10.1)
    # =========================================================

    def _build_raw_scores(self, base_regime: str) -> Dict[str, float]:
        scores = {r: 0.0 for r in PORTFOLIO_REGIMES}

        for regime in PORTFOLIO_REGIMES:
            if regime == base_regime:
                scores[regime] = 2.0
            else:
                scores[regime] = 0.5

        return scores

    # =========================================================
    # SOFTMAX
    # =========================================================

    def _softmax(self, scores: Dict[str, float]) -> Dict[str, float]:
        scaled = {k: v / self.temperature for k, v in scores.items()}
        max_val = max(scaled.values())

        exp_values = {k: math.exp(v - max_val) for k, v in scaled.items()}
        total = sum(exp_values.values())

        if total == 0:
            return {k: 1.0 / len(scores) for k in scores}

        return {k: v / total for k, v in exp_values.items()}