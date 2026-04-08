from __future__ import annotations

from typing import Dict, List, Tuple, Any

from services.regimes.probabilistic_regime_service import ProbabilisticRegimeService
from config.regimes.regime_portfolios import REGIME_ASSETS


class ProbabilisticSignalBuilder:
    """
    Converts a single deterministic regime into:
    → probabilistic multi-regime signals
    → ready for PortfolioEngineService
    """

    def __init__(self) -> None:
        self.regime_service = ProbabilisticRegimeService()

    # =========================================================
    # MAIN
    # =========================================================

    def build_signals(
        self,
        raw_regime: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:

        regime_result = self.regime_service.compute_regime_probabilities(raw_regime)
        probabilities = regime_result["probabilities"]

        final_scores: Dict[str, float] = {}

        for regime, prob in probabilities.items():
            assets = REGIME_ASSETS.get(regime, [])

            for i, asset in enumerate(assets):
                base_score = 1.0 - (i * 0.1)
                weighted_score = prob * base_score

                final_scores[asset] = final_scores.get(asset, 0.0) + weighted_score

        signals: List[Dict[str, Any]] = []

        for asset, score in final_scores.items():
            signals.append(
                {
                    "symbol": asset,
                    "score": round(score, 6),
                    "confidence": 0.7,
                    "direction": "probabilistic_regime",
                    "forecast": None,
                    "asset_name": asset,
                    "asset_class": "probabilistic",
                }
            )

        signals.sort(key=lambda x: x["score"], reverse=True)

        return signals, regime_result