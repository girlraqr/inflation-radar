from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class MappingTheme:
    """
    A theme is an intermediate economic expression that maps into
    one or more tradable assets.

    Example:
        long_duration -> {"TLT": 0.70, "IEF": 0.30}
    """
    name: str
    description: str
    assets: Dict[str, float]


# -------------------------------------------------------------------
# Tradable theme baskets
# -------------------------------------------------------------------

THEME_LONG_DURATION = MappingTheme(
    name="long_duration",
    description="Inflation cooling / growth softening / duration favorable",
    assets={
        "TLT": 0.70,
        "IEF": 0.30,
    },
)

THEME_EQUITIES = MappingTheme(
    name="equities",
    description="Disinflation / risk assets supported / broad equity exposure",
    assets={
        "SPY": 0.65,
        "QQQ": 0.35,
    },
)

THEME_COMMODITIES = MappingTheme(
    name="commodities",
    description="Inflation spike / real asset hedge / commodity exposure",
    assets={
        "DBC": 0.65,
        "GLD": 0.35,
    },
)

THEME_DEFENSIVE = MappingTheme(
    name="defensive",
    description="Capital preservation / defensive posture / short duration",
    assets={
        "SHY": 1.00,
    },
)

THEME_TIPS = MappingTheme(
    name="tips",
    description="Sticky inflation / inflation protection",
    assets={
        "TIP": 1.00,
    },
)

THEME_BALANCED_RISK = MappingTheme(
    name="balanced_risk",
    description="Moderate pro-risk expression",
    assets={
        "SPY": 0.50,
        "IEF": 0.25,
        "GLD": 0.25,
    },
)

THEME_REAL_ASSETS = MappingTheme(
    name="real_assets",
    description="Reflation / nominal growth / real-asset participation",
    assets={
        "DBC": 0.50,
        "SPY": 0.30,
        "GLD": 0.20,
    },
)


# -------------------------------------------------------------------
# Canonical signal aliases
# -------------------------------------------------------------------

SIGNAL_ALIASES: Dict[str, str] = {
    "inflation_cooling": "inflation_cooling",
    "cooling": "inflation_cooling",
    "cpi_cooling": "inflation_cooling",

    "disinflation": "disinflation",
    "disinflationary": "disinflation",

    "inflation_spike": "inflation_spike",
    "spike": "inflation_spike",
    "inflation_reacceleration": "inflation_spike",

    "inflation_sticky": "inflation_sticky",
    "sticky_inflation": "inflation_sticky",

    "reflation": "reflation",
    "reflationary": "reflation",

    "risk_off": "risk_off",
    "defensive": "risk_off",
    "growth_scare": "risk_off",

    "neutral": "neutral",
}


# -------------------------------------------------------------------
# Signal -> primary / secondary theme map
# Each tuple entry is:
#   (theme_name, theme_weight)
# Theme weights should sum to 1.0
# -------------------------------------------------------------------

SIGNAL_THEME_MAP: Dict[str, Tuple[Tuple[str, float], ...]] = {
    "inflation_cooling": (
        ("long_duration", 0.75),
        ("equities", 0.25),
    ),
    "disinflation": (
        ("equities", 0.80),
        ("long_duration", 0.20),
    ),
    "inflation_spike": (
        ("commodities", 0.75),
        ("tips", 0.25),
    ),
    "inflation_sticky": (
        ("tips", 0.60),
        ("commodities", 0.25),
        ("defensive", 0.15),
    ),
    "reflation": (
        ("real_assets", 0.60),
        ("equities", 0.40),
    ),
    "risk_off": (
        ("defensive", 0.70),
        ("long_duration", 0.30),
    ),
    "neutral": (
        ("balanced_risk", 1.00),
    ),
}


# -------------------------------------------------------------------
# Theme registry
# -------------------------------------------------------------------

THEME_REGISTRY: Dict[str, MappingTheme] = {
    THEME_LONG_DURATION.name: THEME_LONG_DURATION,
    THEME_EQUITIES.name: THEME_EQUITIES,
    THEME_COMMODITIES.name: THEME_COMMODITIES,
    THEME_DEFENSIVE.name: THEME_DEFENSIVE,
    THEME_TIPS.name: THEME_TIPS,
    THEME_BALANCED_RISK.name: THEME_BALANCED_RISK,
    THEME_REAL_ASSETS.name: THEME_REAL_ASSETS,
}


# -------------------------------------------------------------------
# Regime adjustments
# Multipliers tilt theme usage depending on macro regime.
# Missing theme => 1.0
# -------------------------------------------------------------------

REGIME_THEME_TILTS: Dict[str, Dict[str, float]] = {
    "cooling": {
        "long_duration": 1.20,
        "equities": 1.05,
        "commodities": 0.85,
    },
    "disinflation": {
        "equities": 1.20,
        "long_duration": 1.10,
        "commodities": 0.80,
        "tips": 0.85,
    },
    "inflation_spike": {
        "commodities": 1.25,
        "tips": 1.10,
        "equities": 0.80,
        "long_duration": 0.75,
    },
    "reflation": {
        "real_assets": 1.20,
        "equities": 1.10,
        "long_duration": 0.85,
    },
    "risk_off": {
        "defensive": 1.25,
        "long_duration": 1.10,
        "equities": 0.75,
        "commodities": 0.90,
    },
    "neutral": {},
}


DEFAULT_REGIME = "neutral"
DEFAULT_SIGNAL = "neutral"
DEFAULT_UNKNOWN_SIGNAL_THEME = "defensive"