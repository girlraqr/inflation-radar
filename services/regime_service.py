from services.inflation_service import InflationService
from models.regime.regime_engine import detect_regime


class RegimeService:

    @staticmethod
    def get_regime():

        inflation_data = InflationService.get_inflation_data()

        inflation_value = float(inflation_data.get("real_inflation", 0))

        regime = detect_regime(inflation_value)

        return {
            "regime": regime,
            "real_inflation": inflation_value,
            "nowcast": inflation_data.get("nowcast_value"),
        }