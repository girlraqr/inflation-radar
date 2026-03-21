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