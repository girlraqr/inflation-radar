from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class SignalResult:
    regime: str
    confidence: float
    inflation_direction: str
    inflation_momentum: str
    bond_signal: str
    equity_signal: str
    usd_signal: str
    gold_signal: str
    summary: str
    details: Dict[str, Any]


class AssetSignals:
    """
    Signal Engine v3
    """

    def generate_signals(self, data: Dict[str, Any]) -> Dict[str, Any]:

        current = float(data["current_inflation"])
        f1 = float(data["forecast_1m"])
        f3 = float(data["forecast_3m"])
        f6 = float(data["forecast_6m"])

        delta_1m = f1 - current
        delta_3m = f3 - current
        delta_6m = f6 - current

        # ------------------------------
        # Direction
        # ------------------------------
        if delta_3m < -0.25 and delta_6m < -0.25:
            direction = "falling"
        elif delta_3m > 0.25 and delta_6m > 0.25:
            direction = "rising"
        else:
            direction = "stable"

        # ------------------------------
        # Momentum
        # ------------------------------
        if delta_1m < delta_3m < delta_6m:
            momentum = "accelerating_up"
        elif delta_1m > delta_3m > delta_6m:
            momentum = "accelerating_down"
        else:
            momentum = "mixed"

        # ------------------------------
        # Regime
        # ------------------------------
        avg_forecast = (f3 + f6) / 2

        if direction == "falling":
            if avg_forecast < 2.5:
                regime = "disinflation"
            else:
                regime = "cooling_inflation"

        elif direction == "rising":
            if avg_forecast > 3.5:
                regime = "reflation"
            else:
                regime = "sticky_inflation"

        else:
            regime = "neutral"

        # ------------------------------
        # Confidence
        # ------------------------------
        confidence = min(
            1.0,
            (abs(delta_1m) + abs(delta_3m) + abs(delta_6m)) / 3
        )

        # ------------------------------
        # Signals
        # ------------------------------

        # Bonds
        if direction == "falling":
            bond_signal = "long_duration"
        elif direction == "rising":
            bond_signal = "short_duration"
        else:
            bond_signal = "neutral"

        # Equity
        if regime in ["disinflation"]:
            equity_signal = "bullish_growth"
        elif regime in ["reflation", "sticky_inflation"]:
            equity_signal = "value_over_growth"
        else:
            equity_signal = "neutral"

        # USD
        if direction == "rising":
            usd_signal = "usd_positive"
        elif direction == "falling":
            usd_signal = "usd_negative"
        else:
            usd_signal = "neutral"

        # Gold
        if direction == "falling":
            gold_signal = "gold_positive"
        elif direction == "rising":
            gold_signal = "gold_hedge"
        else:
            gold_signal = "neutral"

        result = SignalResult(
            regime=regime,
            confidence=round(confidence, 3),
            inflation_direction=direction,
            inflation_momentum=momentum,
            bond_signal=bond_signal,
            equity_signal=equity_signal,
            usd_signal=usd_signal,
            gold_signal=gold_signal,
            summary=f"{regime} | bonds={bond_signal} | eq={equity_signal}",
            details={
                "current": current,
                "f1": f1,
                "f3": f3,
                "f6": f6,
            }
        )

        return asdict(result)