from typing import Dict, Any

import pandas as pd

from models.signals.asset_signals import AssetSignals
from services.forecast_service import ForecastService


class SignalService:
    """
    Signal Service v4

    Pipeline:
    ForecastService → echte Inflation → Signal Engine
    """

    def __init__(self):
        self.forecast_service = ForecastService()
        self.signal_engine = AssetSignals()

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def get_signals(self) -> Dict[str, Any]:
        """
        Hauptfunktion:
        Holt Forecasts + echte Inflation und generiert Signale
        """

        forecast_data = self._get_forecast_data()

        signals = self.signal_engine.generate_signals(forecast_data)

        # 🔥 CLEAN API OUTPUT
        return {
            "macro": {
                "current_inflation": forecast_data["current_inflation"],
                "forecast_1m": forecast_data["forecast_1m"],
                "forecast_3m": forecast_data["forecast_3m"],
                "forecast_6m": forecast_data["forecast_6m"],
            },
            "signals": signals,
        }

    # --------------------------------------------------
    # FORECAST + REAL CPI
    # --------------------------------------------------

    def _get_forecast_data(self) -> Dict[str, float]:
        """
        Kombiniert:
        - echte aktuelle Inflation (CPI YoY)
        - ML Forecasts (1M / 3M / 6M)
        """

        forecast = self.forecast_service.get_inflation_forecast()
        forecasts = forecast["forecasts"]

        # ML Forecasts
        f1 = forecasts["1m"]["forecast"]
        f3 = forecasts["3m"]["forecast"]
        f6 = forecasts["6m"]["forecast"]

        # echte Inflation
        current = self._get_latest_cpi_yoy()

        return {
            "current_inflation": float(current),
            "forecast_1m": float(f1),
            "forecast_3m": float(f3),
            "forecast_6m": float(f6),
        }

    # --------------------------------------------------
    # REAL CPI
    # --------------------------------------------------

    def _get_latest_cpi_yoy(self) -> float:
        """
        Holt die echte aktuelle Inflation (CPI YoY)
        aus deinem ML Dataset
        """

        df = pd.read_csv(
            "storage/cache/ml_dataset.csv",
            index_col="date",
            parse_dates=True
        )

        if "cpi_yoy" not in df.columns:
            raise ValueError("cpi_yoy fehlt im Dataset")

        series = df["cpi_yoy"].dropna()

        if len(series) == 0:
            raise ValueError("Keine gültigen cpi_yoy Werte gefunden")

        latest_value = series.iloc[-1]

        return float(latest_value)