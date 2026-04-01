from __future__ import annotations

from math import sqrt
from typing import Any, Dict, List, Optional

from live.repository.risk_score_config_repository import RiskScoreConfigRepository


class RiskScoreEngineService:
    """
    DB-driven Risk Score Engine

    Berechnet:
    - confidence_score
    - risk_score

    anhand konfigurierbarer Gewichte aus der Datenbank.
    """

    def __init__(
        self,
        repository: Optional[RiskScoreConfigRepository] = None,
    ) -> None:
        self.repository = repository or RiskScoreConfigRepository()

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(maximum, float(value)))

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _get_active_config(self) -> Dict[str, Any]:
        config = self.repository.get_active_config()
        if config is not None:
            return config

        return {
            "profile_name": "in_memory_default",
            "confidence_weight_strength": 0.50,
            "confidence_weight_agreement": 0.25,
            "confidence_weight_breadth": 0.25,
            "risk_weight_inverse_strength": 0.35,
            "risk_weight_dispersion": 0.20,
            "risk_weight_concentration": 0.30,
            "risk_weight_drawdown": 0.15,
            "breadth_full_score_at": 5,
            "drawdown_full_penalty_at": 0.20,
        }

    def _extract_signal_strength(self, signal: Any) -> float:
        if signal is None:
            return 0.5

        if isinstance(signal, dict):
            for key in ("conviction", "confidence", "probability", "strength"):
                if key in signal:
                    return self._clamp(self._safe_float(signal.get(key), 0.5))

            if "score" in signal:
                score_value = self._safe_float(signal.get("score"), 50.0)
                if score_value > 1.0:
                    return self._clamp(score_value / 100.0)
                return self._clamp(score_value)

            return 0.5

        for attr in ("conviction", "confidence", "probability", "strength"):
            if hasattr(signal, attr):
                return self._clamp(self._safe_float(getattr(signal, attr), 0.5))

        if hasattr(signal, "score"):
            score_value = self._safe_float(getattr(signal, "score"), 50.0)
            if score_value > 1.0:
                return self._clamp(score_value / 100.0)
            return self._clamp(score_value)

        return 0.5

    def _extract_signal_direction(self, signal: Any) -> str:
        if signal is None:
            return "neutral"

        if isinstance(signal, dict):
            for key in ("direction", "signal", "canonical_signal", "regime"):
                value = str(signal.get(key, "")).strip().lower()
                if value:
                    return value
            return "neutral"

        for attr in ("direction", "signal", "canonical_signal", "regime"):
            if hasattr(signal, attr):
                value = str(getattr(signal, attr, "")).strip().lower()
                if value:
                    return value

        return "neutral"

    def _compute_signal_dispersion(self, strengths: List[float]) -> float:
        if not strengths:
            return 0.5

        mean_value = sum(strengths) / len(strengths)
        variance = sum((value - mean_value) ** 2 for value in strengths) / len(strengths)
        std_dev = sqrt(variance)
        return self._clamp(std_dev / 0.5)

    def _compute_direction_agreement(self, directions: List[str]) -> float:
        if not directions:
            return 0.5

        buckets: Dict[str, int] = {}
        for direction in directions:
            buckets[direction] = buckets.get(direction, 0) + 1

        dominant_share = max(buckets.values()) / len(directions)
        return self._clamp(dominant_share)

    def _compute_breadth_score(self, signal_count: int, breadth_full_score_at: int) -> float:
        if signal_count <= 0:
            return 0.0
        return self._clamp(signal_count / max(1, breadth_full_score_at))

    def _compute_concentration_score(self, portfolio: Optional[Dict[str, Any]]) -> float:
        if not portfolio:
            return 0.5

        positions = portfolio.get("positions", [])
        if not positions:
            return 0.5

        weights: List[float] = []
        for position in positions:
            weight = self._safe_float(position.get("target_weight"), 0.0)
            if weight > 0:
                weights.append(weight)

        if not weights:
            return 0.5

        max_weight = max(weights)
        hhi = sum(weight ** 2 for weight in weights)

        normalized_hhi = self._clamp((hhi - 0.15) / 0.45)
        normalized_max_weight = self._clamp((max_weight - 0.20) / 0.50)

        concentration = (0.55 * normalized_max_weight) + (0.45 * normalized_hhi)
        return self._clamp(concentration)

    def _compute_drawdown_penalty(
        self,
        current_drawdown: Optional[float],
        drawdown_full_penalty_at: float,
    ) -> float:
        if current_drawdown is None:
            return 0.0

        drawdown = abs(self._safe_float(current_drawdown, 0.0))
        return self._clamp(drawdown / max(0.0001, drawdown_full_penalty_at))

    def calculate_scores(
        self,
        ranked_signals: Optional[List[Any]],
        portfolio: Optional[Dict[str, Any]] = None,
        current_drawdown: Optional[float] = None,
    ) -> Dict[str, Any]:
        ranked_signals = ranked_signals or []
        config = self._get_active_config()

        strengths = [self._extract_signal_strength(signal) for signal in ranked_signals]
        directions = [self._extract_signal_direction(signal) for signal in ranked_signals]

        average_strength = sum(strengths) / len(strengths) if strengths else 0.5
        signal_dispersion = self._compute_signal_dispersion(strengths)
        direction_agreement = self._compute_direction_agreement(directions)
        breadth_score = self._compute_breadth_score(
            len(ranked_signals),
            int(config["breadth_full_score_at"]),
        )
        concentration_score = self._compute_concentration_score(portfolio)
        drawdown_penalty = self._compute_drawdown_penalty(
            current_drawdown=current_drawdown,
            drawdown_full_penalty_at=float(config["drawdown_full_penalty_at"]),
        )

        cw_strength = float(config["confidence_weight_strength"])
        cw_agreement = float(config["confidence_weight_agreement"])
        cw_breadth = float(config["confidence_weight_breadth"])
        cw_total = cw_strength + cw_agreement + cw_breadth

        rw_inverse_strength = float(config["risk_weight_inverse_strength"])
        rw_dispersion = float(config["risk_weight_dispersion"])
        rw_concentration = float(config["risk_weight_concentration"])
        rw_drawdown = float(config["risk_weight_drawdown"])
        rw_total = rw_inverse_strength + rw_dispersion + rw_concentration + rw_drawdown

        confidence_raw = (
            (cw_strength * average_strength)
            + (cw_agreement * direction_agreement)
            + (cw_breadth * breadth_score)
        ) / max(0.0001, cw_total)

        risk_raw = (
            (rw_inverse_strength * (1.0 - average_strength))
            + (rw_dispersion * signal_dispersion)
            + (rw_concentration * concentration_score)
            + (rw_drawdown * drawdown_penalty)
        ) / max(0.0001, rw_total)

        confidence_score = self._clamp(confidence_raw)
        risk_score = self._clamp(risk_raw)

        return {
            "profile_name": config["profile_name"],
            "confidence_score": round(confidence_score, 6),
            "risk_score": round(risk_score, 6),
            "components": {
                "average_strength": round(average_strength, 6),
                "signal_dispersion": round(signal_dispersion, 6),
                "direction_agreement": round(direction_agreement, 6),
                "breadth_score": round(breadth_score, 6),
                "concentration_score": round(concentration_score, 6),
                "drawdown_penalty": round(drawdown_penalty, 6),
                "signal_count": len(ranked_signals),
            },
            "weights": {
                "confidence_weight_strength": cw_strength,
                "confidence_weight_agreement": cw_agreement,
                "confidence_weight_breadth": cw_breadth,
                "risk_weight_inverse_strength": rw_inverse_strength,
                "risk_weight_dispersion": rw_dispersion,
                "risk_weight_concentration": rw_concentration,
                "risk_weight_drawdown": rw_drawdown,
            },
        }