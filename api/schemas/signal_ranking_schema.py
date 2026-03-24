from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RankedSignalFreeResponseItem(BaseModel):
    rank: int = Field(..., ge=1)
    asset: str
    teaser_score: float
    signal: str
    confidence: float
    signal_strength: str


class RankedSignalPremiumResponseItem(BaseModel):
    rank: int = Field(..., ge=1)
    asset: str
    score: float
    signal: str
    confidence: float
    forecast_1m: Optional[float] = None
    forecast_3m: Optional[float] = None
    forecast_6m: Optional[float] = None
    cpi_yoy: Optional[float] = None
    regime: Optional[str] = None
    rationale: str
    allocation_hint: Optional[float] = None


class RankedSignalsFreeResponse(BaseModel):
    plan: str
    count: int
    summary: Dict[str, Any]
    signals: List[RankedSignalFreeResponseItem]


class RankedSignalsPremiumResponse(BaseModel):
    plan: str
    count: int
    summary: Dict[str, Any]
    signals: List[RankedSignalPremiumResponseItem]