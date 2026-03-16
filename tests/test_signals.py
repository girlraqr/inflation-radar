from models.signals.asset_signals import gold_signal
from models.regime.regime_engine import inflation_regime


def test_gold_signal():

    signal = gold_signal(real_inflation=6, interest_rate=2)

    assert signal in [
        "STRONG GOLD SIGNAL",
        "GOLD POSITIVE",
        "NEUTRAL"
    ]


def test_inflation_regime():

    regime = inflation_regime(5)

    assert regime in [
        "LOW INFLATION",
        "MODERATE INFLATION",
        "HIGH INFLATION REGIME"
    ]