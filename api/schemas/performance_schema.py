from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SignalRuleStatsSchema(BaseModel):
    label: str
    hits: int
    total: int
    hit_rate: float


class SignalAccuracySchema(BaseModel):
    overall_hit_rate: float
    total_signals: int
    hits: int
    by_signal: dict[str, SignalRuleStatsSchema]


class IntelligenceNarrativeSchema(BaseModel):
    title: str
    status: str
    hit_rate: float
    message: str


class IntelligenceOverlaySchema(BaseModel):
    recent_3m_momentum: float
    current_drawdown: float
    signal_backing_strength: float
    narratives: list[IntelligenceNarrativeSchema]


class PortfolioPerformanceSummarySchema(BaseModel):
    observations: int
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    latest_value: float
    latest_period_return: float
    latest_cumulative_return: float


class PortfolioHistoryPointSchema(BaseModel):
    date: str
    period_return: float
    portfolio_value: float
    cumulative_return: float
    rolling_peak: float
    drawdown: float
    weights: dict[str, float]


class PortfolioPerformanceResponseSchema(BaseModel):
    summary: PortfolioPerformanceSummarySchema
    signal_accuracy: SignalAccuracySchema
    intelligence: IntelligenceOverlaySchema
    meta: dict[str, Any] | None = None


class PortfolioHistoryResponseSchema(BaseModel):
    history: list[PortfolioHistoryPointSchema]
    count: int = Field(..., ge=0)