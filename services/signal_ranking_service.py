from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import math


@dataclass
class RankedSignal:
    rank: int
    asset: str
    score: float
    signal: str
    confidence: float
    forecast_1m: Optional[float]
    forecast_3m: Optional[float]
    forecast_6m: Optional[float]
    cpi_yoy: Optional[float]
    regime: Optional[str]
    rationale: str
    allocation_hint: Optional[float]


class SignalRankingService:

    BULLISH_WORDS = {"buy", "overweight", "bullish", "risk_on", "long", "positive"}
    BEARISH_WORDS = {"sell", "underweight", "bearish", "risk_off", "short", "negative"}
    NEUTRAL_WORDS = {"hold", "neutral", "market_weight", "flat"}

    # =========================================================
    # 🔥 PORTFOLIO ENTRYPOINT
    # =========================================================

    def get_ranked_signals(
        self,
        user_id: int,
        premium: bool = True,
    ) -> List[Dict[str, Any]]:

        raw_signals = self._load_raw_signals(user_id=user_id)
        ranked = self._build_ranked_signals(raw_signals)

        results: List[Dict[str, Any]] = []

        for item in ranked:
            results.append(
                {
                    "symbol": item.asset,
                    "score": item.score,
                    "confidence": item.confidence,
                    "direction": item.signal,
                    "forecast": item.forecast_3m,
                    "asset_name": item.asset,
                    "asset_class": item.regime,
                }
            )

        return results

    # =========================================================
    # 🔧 TEMP DATA (ersetzen später)
    # =========================================================

    def _load_raw_signals(self, user_id: int) -> List[Dict[str, Any]]:
        return [
            {
                "asset": "CPI_US",
                "signal": "buy",
                "score": 85,
                "confidence": 0.82,
                "forecast_3m": 0.35,
                "cpi_yoy": 3.2,
                "regime": "macro",
            },
            {
                "asset": "DGS10",
                "signal": "buy",
                "score": 72,
                "confidence": 0.75,
                "forecast_3m": 0.20,
                "cpi_yoy": 3.2,
                "regime": "rates",
            },
            {
                "asset": "GOLD",
                "signal": "hold",
                "score": 55,
                "confidence": 0.65,
                "forecast_3m": 0.10,
                "cpi_yoy": 3.2,
                "regime": "commodities",
            },
        ]

    # =========================================================
    # CORE RANKING
    # =========================================================

    def _build_ranked_signals(self, raw_signals: List[Dict[str, Any]]) -> List[RankedSignal]:

        scored_items: List[RankedSignal] = []

        for item in raw_signals:

            asset = self._first_str(item, ["asset", "ticker", "symbol", "name"], default="UNKNOWN")
            signal = self._first_str(item, ["signal", "direction", "stance"], default="neutral").lower()

            forecast_1m = self._first_float(item, ["forecast_1m"])
            forecast_3m = self._first_float(item, ["forecast_3m"])
            forecast_6m = self._first_float(item, ["forecast_6m"])
            cpi_yoy = self._first_float(item, ["cpi_yoy"])

            confidence = self._clamp(
                self._first_float(item, ["confidence"], default=0.5),
                0.0,
                1.0,
            )

            regime = self._first_optional_str(item, ["regime"])

            raw_score = self._first_float(item, ["score"], default=50.0)
            score = round(float(raw_score), 4)

            allocation_hint = self._allocation_hint(score)

            rationale = f"signal={signal} | confidence={confidence:.2f}"

            scored_items.append(
                RankedSignal(
                    rank=0,
                    asset=asset,
                    score=score,
                    signal=signal,
                    confidence=round(confidence, 4),
                    forecast_1m=forecast_1m,
                    forecast_3m=forecast_3m,
                    forecast_6m=forecast_6m,
                    cpi_yoy=cpi_yoy,
                    regime=regime,
                    rationale=rationale,
                    allocation_hint=allocation_hint,
                )
            )

        scored_items.sort(key=lambda x: (-x.score, -x.confidence))

        for idx, item in enumerate(scored_items, start=1):
            item.rank = idx

        return scored_items

    # =========================================================
    # LOGIC
    # =========================================================

    def _allocation_hint(self, score: float) -> float:
        if score >= 85:
            return 0.22
        if score >= 75:
            return 0.18
        if score >= 65:
            return 0.14
        if score >= 55:
            return 0.10
        if score >= 45:
            return 0.07
        return 0.04

    # =========================================================
    # HELPERS (WICHTIG!)
    # =========================================================

    def _first_str(self, data: Dict[str, Any], keys: List[str], default: str) -> str:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return default

    def _first_optional_str(self, data: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _first_float(
        self,
        data: Dict[str, Any],
        keys: List[str],
        default: Optional[float] = None,
    ) -> Optional[float]:
        for key in keys:
            if key not in data:
                continue

            value = data.get(key)

            try:
                if value is not None:
                    return float(value)
            except (TypeError, ValueError):
                continue

        return default

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))