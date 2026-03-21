from fastapi import APIRouter
from api.schemas.forecast_schema import ForecastResponse
from services.forecast_service import ForecastService

router = APIRouter()
service = ForecastService()

@router.get("/forecast/inflation", response_model=ForecastResponse)
def forecast_inflation():
    return ForecastService.get_inflation_forecast()