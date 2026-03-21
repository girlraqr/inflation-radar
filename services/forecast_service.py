import pandas as pd

from models.ml.forecast_service import MLForecastService


class ForecastService:
    """
    High-level forecast service.

    Verantwortlich für:
    - Raw Predictions abrufen
    - Delta -> Level Rekonstruktion
    - Optionale Level Calibration
    - Finales Forecast-Response bauen
    """

    def __init__(
        self,
        model_dir: str = "storage/cache",
        use_level_calibration: bool = False,
        calibration_weight_current: float = 0.7,
        calibration_weight_model: float = 0.3,
    ):
        self.ml_service = MLForecastService(model_dir=model_dir)

        self.use_level_calibration = use_level_calibration
        self.calibration_weight_current = calibration_weight_current
        self.calibration_weight_model = calibration_weight_model

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    @staticmethod
    def get_current_inflation(df: pd.DataFrame) -> float:
        if "cpi_yoy" not in df.columns:
            raise ValueError("[ERROR] 'cpi_yoy' nicht im Feature-Datensatz vorhanden")

        return float(df["cpi_yoy"].iloc[-1])

    @staticmethod
    def reconstruct_level_forecast(raw_pred: float, current_value: float, horizon: str) -> float:
        """
        1m = direktes Level
        3m/6m = Delta-Target -> zurück auf Level
        """
        if horizon in ["3m", "6m"]:
            return float(current_value + raw_pred)

        return float(raw_pred)

    def apply_level_calibration(self, current_value: float, forecast_value: float) -> float:
        return float(
            self.calibration_weight_current * current_value
            + self.calibration_weight_model * forecast_value
        )

    def build_forecast_entry(self, current_value: float, raw_pred: float, horizon: str) -> dict:
        raw_level = self.reconstruct_level_forecast(raw_pred, current_value, horizon)

        if self.use_level_calibration:
            final_forecast = self.apply_level_calibration(current_value, raw_level)
        else:
            final_forecast = raw_level

        return {
            "raw_prediction": float(raw_pred),      # bei 3m/6m = delta raw
            "raw_forecast": float(raw_level),       # immer auf Level rekonstruiert
            "forecast": float(final_forecast),      # optional kalibriert
            "delta_vs_current": float(raw_level - current_value),
        }

    # --------------------------------------------------
    # MAIN FORECAST
    # --------------------------------------------------

    def generate_forecast(self, df: pd.DataFrame) -> dict:
        current = self.get_current_inflation(df)

        raw_preds = self.ml_service.predict_raw(df)

        one_m = self.build_forecast_entry(current, raw_preds["1m"], "1m")
        three_m = self.build_forecast_entry(current, raw_preds["3m"], "3m")
        six_m = self.build_forecast_entry(current, raw_preds["6m"], "6m")

        result = {
            "current": float(current),

            "raw_prediction_1m": one_m["raw_prediction"],
            "raw_prediction_3m": three_m["raw_prediction"],
            "raw_prediction_6m": six_m["raw_prediction"],

            "raw_forecast_1m": one_m["raw_forecast"],
            "raw_forecast_3m": three_m["raw_forecast"],
            "raw_forecast_6m": six_m["raw_forecast"],

            "forecast_1m": one_m["forecast"],
            "forecast_3m": three_m["forecast"],
            "forecast_6m": six_m["forecast"],

            "delta_1m": one_m["delta_vs_current"],
            "delta_3m": three_m["delta_vs_current"],
            "delta_6m": six_m["delta_vs_current"],

            "metadata": {
                "use_level_calibration": self.use_level_calibration,
                "calibration_weight_current": self.calibration_weight_current,
                "calibration_weight_model": self.calibration_weight_model,
            }
        }

        return result