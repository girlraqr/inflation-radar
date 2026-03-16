from services.regime_service import get_regime
from services.inflation_service import get_inflation_data
from models.signals.asset_signals import gold_signal


def get_signals():
    regime_data = get_regime()
    inflation_data = get_inflation_data()

    regime = regime_data["regime"]
    real_inflation_value = float(inflation_data.get("nowcast_value", 0))
    interest_rate = float(inflation_data.get("monetary_score", 0))

    signal = gold_signal(real_inflation_value, interest_rate)

    return {
        "regime": regime,
        "gold_signal": signal,
    }