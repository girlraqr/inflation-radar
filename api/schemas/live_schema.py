from __future__ import annotations

from datetime import datetime, date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AllocationItemSchema(BaseModel):
    asset: str = Field(..., description="ETF oder Asset-Ticker")
    weight: float = Field(..., description="Zielgewicht zwischen 0 und 1")


class LiveSignalResponseSchema(BaseModel):
    as_of_date: date
    published_at: datetime
    regime: str
    regime_score: float
    signal_strength: float
    confidence: float
    rebalance_flag: bool
    top_n: int
    ranking: List[str]
    allocation: List[AllocationItemSchema]
    meta: Dict[str, str]


class LiveStatusResponseSchema(BaseModel):
    status: str
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    message: Optional[str] = None


class LiveHistoryItemSchema(BaseModel):
    as_of_date: date
    regime: str
    confidence: float
    signal_strength: float
    rebalance_flag: bool