from pydantic import BaseModel
from typing import Dict


class ForecastResponse(BaseModel):
    forecast_3m: float
    rmse: float
    r2: float
    feature_importance: Dict[str, float]