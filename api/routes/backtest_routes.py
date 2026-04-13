from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

# Schemas
from api.schemas.backtest_schema import (
    BacktestRequest,
    BacktestResponse,
    BacktestRunRequest,
    BacktestRunResponse,
)

# Services (bestehender Endpoint nutzt das weiterhin)
from services.backtest_service import BacktestService

# Engine (für neuen Endpoint)
from models.backtest.backtest_engine import BacktestEngine, BacktestConfig


# --------------------------------------------------
# ROUTER INIT
# --------------------------------------------------

router = APIRouter(prefix="/backtest", tags=["backtest"])

# ⚠️ Bestehender Service bleibt für Legacy Endpoint
service = BacktestService()


# --------------------------------------------------
# EXISTING ENDPOINT (UNVERÄNDERT)
# --------------------------------------------------

@router.post("/", response_model=BacktestResponse)
def run_backtest(request: BacktestRequest) -> BacktestResponse:
    signals_df = pd.read_csv(request.signals_path)
    returns_df = pd.read_csv(request.returns_path)

    service.engine.config.transaction_cost_bps = request.transaction_cost_bps

    result = service.run_backtest(
        signals_df=signals_df,
        returns_df=returns_df,
    )

    return BacktestResponse(
        metrics=result["metrics"],
        regime_breakdown=result.get("regime_breakdown", {}),
        timeseries=result["timeseries"].to_dict(orient="records"),
        weights=result["weights"].to_dict(orient="records"),
    )


# --------------------------------------------------
# NEW ENDPOINT: POST /backtest/run
# --------------------------------------------------

@router.post("/run", response_model=BacktestRunResponse)
def run_backtest_with_config(request: BacktestRunRequest) -> BacktestRunResponse:

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    signals_df = pd.read_csv(request.signals_path)
    returns_df = pd.read_csv(request.returns_path)

    cfg = request.config

    # -----------------------------
    # % → BPS CONVERSION
    # -----------------------------
    transaction_cost_bps = cfg.transaction_cost_pct * 100.0
    slippage_bps = cfg.slippage_pct * 100.0

    # -----------------------------
    # CREATE NEW ENGINE (THREAD-SAFE)
    # -----------------------------
    engine = BacktestEngine(
        config=BacktestConfig(
            smoothing_alpha=cfg.alpha,
            gamma=cfg.gamma,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
            include_costs=cfg.include_costs,
        )
    )

    # -----------------------------
    # RUN BACKTEST
    # -----------------------------
    result = engine.run(
        signals_df=signals_df,
        returns_df=returns_df,
    )

    # -----------------------------
    # RESPONSE
    # -----------------------------
    return BacktestRunResponse(
        metrics=result["metrics"],
        timeseries=result["timeseries"].to_dict(orient="records"),
        weights=result["weights"].to_dict(orient="records"),
    )