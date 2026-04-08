from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

import pandas as pd


@dataclass(frozen=True)
class BaselineRegimeMapperConfig:
    temperature: float = 0.70
    reflation_prob_weight: float = 1.20
    reflation_term_weight: float = 0.60
    neutral_anchor: float = 0.35
    neutral_uncertainty_penalty: float = 0.80


class BaselineRegimeProbabilityMapper:
    """
    Phase 10.3 baseline mapper

    Nutzt nur die aktuell vorhandenen Features aus signal_history.csv:
    - regime
    - prob_3m
    - prob_6m

    Ziel:
    - aus Label + Horizon-Probs eine weiche Regime-Verteilung bauen
    - aktuell primär für investierbare Regimes:
        * short_term_reflation
        * neutral
    """

    def __init__(self, config: BaselineRegimeMapperConfig | None = None) -> None:
        self.config = config or BaselineRegimeMapperConfig()

    def map_row_to_probabilities(
        self,
        row: Mapping[str, object] | pd.Series,
        allowed_regimes: Iterable[str],
    ) -> Dict[str, float]:
        regimes = list(allowed_regimes)
        if not regimes:
            return {}

        raw_scores = self._build_raw_scores(row=row, allowed_regimes=regimes)
        probs = self._softmax(raw_scores, temperature=self.config.temperature)
        return probs

    def _build_raw_scores(
        self,
        row: Mapping[str, object] | pd.Series,
        allowed_regimes: list[str],
    ) -> Dict[str, float]:
        raw_regime = str(row.get("regime", "neutral") or "neutral").lower().strip()

        prob_3m = self._safe_prob(row.get("prob_3m"))
        prob_6m = self._safe_prob(row.get("prob_6m"))

        avg_prob = (prob_3m + prob_6m) / 2.0
        term_delta = prob_3m - prob_6m

        regime_bias = self._regime_bias(raw_regime)

        reflation_score = (
            regime_bias
            + self.config.reflation_prob_weight * (avg_prob - 0.5)
            + self.config.reflation_term_weight * term_delta
        )

        neutral_score = (
            self.config.neutral_anchor
            - self.config.neutral_uncertainty_penalty * abs(avg_prob - 0.5)
        )

        scores: Dict[str, float] = {}

        for regime in allowed_regimes:
            regime_key = str(regime).lower().strip()

            if regime_key == "short_term_reflation":
                scores[regime] = reflation_score
            elif regime_key == "neutral":
                scores[regime] = neutral_score
            else:
                scores[regime] = self._fallback_score_for_unknown_regime(
                    regime_key=regime_key,
                    raw_regime=raw_regime,
                    avg_prob=avg_prob,
                )

        return scores

    def _regime_bias(self, raw_regime: str) -> float:
        bias_map = {
            "short_term_reflation": 1.10,
            "reflation": 0.90,
            "inflation_bottoming": 0.40,
            "neutral": 0.00,
            "short_term_disinflation": -0.60,
            "disinflation_strong": -0.90,
        }
        return float(bias_map.get(raw_regime, 0.00))

    def _fallback_score_for_unknown_regime(
        self,
        regime_key: str,
        raw_regime: str,
        avg_prob: float,
    ) -> float:
        if regime_key == raw_regime:
            return 0.25 + (avg_prob - 0.5)
        return -0.25

    def _safe_prob(self, value: object) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError):
            result = 0.5

        return max(0.0, min(1.0, result))

    def _softmax(self, scores: Dict[str, float], temperature: float) -> Dict[str, float]:
        if not scores:
            return {}

        temp = max(float(temperature), 1e-6)
        scaled = {k: v / temp for k, v in scores.items()}
        max_val = max(scaled.values())

        exp_values = {k: math.exp(v - max_val) for k, v in scaled.items()}
        total = sum(exp_values.values())

        if total <= 0:
            n = len(scores)
            return {k: 1.0 / n for k in scores}

        return {k: v / total for k, v in exp_values.items()}