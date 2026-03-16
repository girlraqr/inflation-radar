from __future__ import annotations
from typing import Any


def inflation_regime(inflation_value: float) -> str:
    """
    Classify an inflation reading into a macro regime.
    """

    value = float(inflation_value)

    if value < 0:
        return "DEFLATION"

    if value < 2:
        return "LOW INFLATION"

    if value < 4:
        return "MODERATE INFLATION"

    return "HIGH INFLATION REGIME"


def detect_regime(inflation_value: float) -> str:
    """
    Alias for inflation_regime.
    """
    return inflation_regime(inflation_value)


def get_inflation_regime(inflation_value: float) -> str:
    """
    Additional alias for compatibility.
    """
    return inflation_regime(inflation_value)


def classify_regime(payload: Any) -> str:
    """
    Accept float or dict payload.
    """

    if isinstance(payload, (int, float)):
        return inflation_regime(payload)

    if isinstance(payload, dict):

        for key in ["inflation", "yoy", "real_inflation", "value"]:

            if key in payload:
                return inflation_regime(payload[key])

    raise ValueError("Unsupported payload for regime classification")