from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import math


# =========================================================
# CONFIG
# =========================================================

MULTI_REGIMES = (
    "reflation",
    "short_term_reflation",
    "disinflation",
    "short_term_disinflation",
    "neutral",
)


@dataclass
class MultiRegimeMapperConfig:
    temperature: float = 1.0


# =========================================================
# MAPPER
# =========================================================

class MultiRegimeProbabilityMapper:
    def __init__(self, config: MultiRegimeMapperConfig):
        self.config = config

    def map_row_to_probabilities(
        self,
        row,
        allowed_regimes: List[str],
    ) -> Dict[str, float]:

        p3 = float(row.get("prob_3m", 0.5))
        p6 = float(row.get("prob_6m", 0.5))

        p3 = max(0.0, min(1.0, p3))
        p6 = max(0.0, min(1.0, p6))

        raw_scores = self._build_raw_scores(p3, p6)
        probs = self._softmax(raw_scores)

        return {r: probs.get(r, 0.0) for r in allowed_regimes}

    # --------------------------------------------------

    def _build_raw_scores(self, p3: float, p6: float) -> Dict[str, float]:

        scores = {}

        scores["reflation"] = p6 * p3
        scores["short_term_reflation"] = p3 * (1.0 - p6)

        scores["disinflation"] = (1.0 - p6) * (1.0 - p3)
        scores["short_term_disinflation"] = (1.0 - p3) * p6

        neutral_3m = 1.0 - abs(p3 - 0.5) * 2.0
        neutral_6m = 1.0 - abs(p6 - 0.5) * 2.0

        scores["neutral"] = max(0.0, neutral_3m * neutral_6m)

        return scores

    # --------------------------------------------------

    def _softmax(self, scores: Dict[str, float]) -> Dict[str, float]:
        temp = max(1e-6, float(self.config.temperature))

        scaled = {k: v / temp for k, v in scores.items()}
        max_val = max(scaled.values())

        exp_values = {k: math.exp(v - max_val) for k, v in scaled.items()}
        total = sum(exp_values.values())

        if total <= 0:
            return {k: 1.0 / len(scores) for k in scores}

        return {k: v / total for k, v in exp_values.items()}