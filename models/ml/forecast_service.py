import os
import pandas as pd

from models.ml.inflation_model import InflationModel
from models.ml.feature_engineering import FEATURE_SETS


class MLForecastService:
    """
    Low-level ML forecast service.

    Verantwortlich für:
    - Modell laden
    - Feature-Auswahl je Horizon
    - Raw Predictions erzeugen

    Nicht verantwortlich für:
    - Level Calibration
    - API Response Formatting
    - Signal-Logik
    """

    def __init__(self, model_dir: str = "storage/cache"):
        self.model_dir = model_dir
        self.models = {}

    # --------------------------------------------------
    # MODEL LOADING
    # --------------------------------------------------

    def _get_model_path(self, horizon: str) -> str:
        return os.path.join(self.model_dir, f"inflation_model_{horizon}.joblib")

    def load_model(self, horizon: str) -> InflationModel:
        if horizon in self.models:
            return self.models[horizon]

        model_path = self._get_model_path(horizon)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"[ERROR] Modell für {horizon} nicht gefunden: {model_path}"
            )

        model = InflationModel(horizon)
        model.load_model(model_path)

        self.models[horizon] = model
        return model

    def load_all_models(self):
        for horizon in ["1m", "3m", "6m"]:
            self.load_model(horizon)

    # --------------------------------------------------
    # FEATURE PREPARATION
    # --------------------------------------------------

    def prepare_latest_features(self, df: pd.DataFrame, horizon: str) -> pd.DataFrame:
        if horizon not in FEATURE_SETS:
            raise ValueError(f"[ERROR] Unbekannter Horizon: {horizon}")

        features = FEATURE_SETS[horizon]

        missing = [col for col in features if col not in df.columns]
        if missing:
            raise ValueError(
                f"[ERROR] Fehlende Features für {horizon}: {missing}"
            )

        latest = df[features].iloc[[-1]].copy()
        return latest

    # --------------------------------------------------
    # RAW PREDICTION
    # --------------------------------------------------

    def predict_raw_for_horizon(self, df: pd.DataFrame, horizon: str) -> float:
        model = self.load_model(horizon)
        X_latest = self.prepare_latest_features(df, horizon)

        pred = model.predict(X_latest)[0]
        return float(pred)

    def predict_raw(self, df: pd.DataFrame) -> dict:
        """
        Returns raw model predictions:
        - 1m: level prediction
        - 3m: delta prediction
        - 6m: delta prediction
        """
        return {
            "1m": self.predict_raw_for_horizon(df, "1m"),
            "3m": self.predict_raw_for_horizon(df, "3m"),
            "6m": self.predict_raw_for_horizon(df, "6m"),
        }