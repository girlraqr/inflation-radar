from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from api.schemas.backtest_schema import BacktestRequest, BacktestResponse
from services.backtest_service import BacktestService

router = APIRouter(prefix="/backtest", tags=["backtest"])
service = BacktestService()


@router.post("/", response_model=BacktestResponse)
def run_backtest(request: BacktestRequest) -> BacktestResponse:
    signals_df = pd.read_csv(request.signals_path)
    returns_df = pd.read_csv(request.returns_path)

    service.engine.config.transaction_cost_bps = request.transaction_cost_bps
    result = service.run_backtest(signals_df=signals_df, returns_df=returns_df)

    return BacktestResponse(
        metrics=result["metrics"],
        regime_breakdown=result["regime_breakdown"],
        timeseries=result["timeseries"].to_dict(orient="records"),
        weights=result["weights"].to_dict(orient="records"),
    )