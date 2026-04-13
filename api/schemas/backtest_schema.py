from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class BacktestRequest(BaseModel):
    signals_path: str = Field(..., description="CSV path for signal history")
    returns_path: str = Field(..., description="CSV path for asset returns")
    transaction_cost_bps: float = 5.0


class BacktestResponse(BaseModel):
    metrics: Dict[str, Any]
    regime_breakdown: Dict[str, Any]
    timeseries: List[Dict[str, Any]]
    weights: List[Dict[str, Any]]
    
# --------------------------------------------------
# NEW: CONFIG-DRIVEN BACKTEST
# --------------------------------------------------

class BacktestRunConfig(BaseModel):
    alpha: float = Field(0.30, ge=0.0, le=1.0)
    gamma: float = Field(1.35, gt=0.0)

    # INPUT IN %
    transaction_cost_pct: float = Field(0.05, ge=0.0)
    slippage_pct: float = Field(0.00, ge=0.0)

    include_costs: bool = True


class BacktestRunRequest(BaseModel):
    signals_path: str
    returns_path: str
    config: BacktestRunConfig


class BacktestRunResponse(BaseModel):
    metrics: Dict[str, Any]
    timeseries: List[Dict[str, Any]]
    weights: List[Dict[str, Any]]