from services.inflation_service import get_inflation_data
from models.regime.regime_engine import inflation_regime


def get_regime():
    inflation_data = get_inflation_data()

    nowcast_value = float(inflation_data.get("nowcast_value", 0))

    regime = inflation_regime(nowcast_value)

    return {
        "inflation_nowcast": nowcast_value,
        "regime": regime,
    }