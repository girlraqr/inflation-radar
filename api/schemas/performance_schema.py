from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# =========================
# SIGNAL ACCURACY
# =========================

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


# =========================
# INTELLIGENCE
# =========================

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


# =========================
# BASE PERFORMANCE (ALT)
# =========================

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


# =========================
# ALPHA ENGINE (NEU)
# =========================

class AlphaAnalysisSchema(BaseModel):
    return_delta: float
    volatility_reduction: float
    drawdown_reduction: float
    efficiency_score: float


# =========================
# NEUE SUMMARY STRUKTUR
# =========================

class PortfolioPerformanceCompositeSummarySchema(BaseModel):
    base: PortfolioPerformanceSummarySchema
    risk_adjusted: Optional[PortfolioPerformanceSummarySchema]
    alpha_analysis: Optional[AlphaAnalysisSchema]


# =========================
# RESPONSE
# =========================

class PortfolioPerformanceResponseSchema(BaseModel):
    summary: PortfolioPerformanceCompositeSummarySchema
    signal_accuracy: SignalAccuracySchema
    intelligence: IntelligenceOverlaySchema
    meta: dict[str, Any] | None = None


# =========================
# HISTORY
# =========================

class PortfolioHistoryPointSchema(BaseModel):
    date: str
    period_return: float
    portfolio_value: float
    cumulative_return: float
    rolling_peak: float
    drawdown: float
    weights: dict[str, float]


class PortfolioHistoryResponseSchema(BaseModel):
    history: list[PortfolioHistoryPointSchema]
    count: int = Field(..., ge=0)