from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from auth.dependencies import get_current_user
from api.schemas.performance_schema import (
    PortfolioHistoryResponseSchema,
    PortfolioPerformanceResponseSchema,
)
from services.portfolio_engine_service import PortfolioEngineService
from services.portfolio_performance_adapter import PortfolioPerformanceAdapter
from services.signal_ranking_service import SignalRankingService


router = APIRouter(prefix="/portfolio", tags=["portfolio"])

performance_adapter = PortfolioPerformanceAdapter()


# =========================
# RESPONSE MODELS
# =========================

class PortfolioPositionResponse(BaseModel):
    symbol: str
    target_weight: float
    current_weight: float
    delta: float
    score: float
    confidence: float
    direction: str
    forecast: Optional[float] = None
    asset_name: Optional[str] = None
    asset_class: Optional[str] = None
    action: str


class PortfolioResponse(BaseModel):
    user_id: int
    generated_at: str
    rebalance_required: bool
    rebalance_reason: str
    total_invested_weight: float
    cash_weight: float
    allocation_hint: str
    positions: List[PortfolioPositionResponse]
    meta: Dict[str, Any]


# =========================
# HELPERS
# =========================

def _is_premium_user(current_user) -> bool:
    if hasattr(current_user, "subscription_tier"):
        return str(current_user.subscription_tier).lower() == "premium"

    if hasattr(current_user, "is_premium"):
        return current_user.is_premium is True

    if isinstance(current_user, dict):
        if current_user.get("is_premium") is True:
            return True

        plan = str(current_user.get("plan", "")).lower()
        role = str(current_user.get("role", "")).lower()
        subscription = str(current_user.get("subscription_tier", "")).lower()

        return any(v == "premium" for v in [plan, role, subscription])

    return False


def _extract_user_id(current_user) -> int:
    if hasattr(current_user, "id"):
        return int(current_user.id)

    if isinstance(current_user, dict):
        user_id = current_user.get("id") or current_user.get("user_id")
        if user_id is not None:
            return int(user_id)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="User object does not contain an id/user_id field.",
    )


def _mask_free_performance_payload(result: Any) -> Dict[str, Any]:
    return {
        "summary": {
            "observations": result.summary["observations"],
            "total_return": result.summary["total_return"],
            "annualized_return": result.summary["annualized_return"],
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "latest_value": result.summary["latest_value"],
            "latest_period_return": result.summary["latest_period_return"],
            "latest_cumulative_return": result.summary["latest_cumulative_return"],
        },
        "signal_accuracy": {
            "overall_hit_rate": 0.0,
            "total_signals": 0,
            "hits": 0,
            "by_signal": {},
        },
        "intelligence": {
            "recent_3m_momentum": result.intelligence["recent_3m_momentum"],
            "current_drawdown": result.intelligence["current_drawdown"],
            "signal_backing_strength": 0.0,
            "narratives": [],
        },
        "meta": result.meta,
    }


def _add_snapshot_comparison(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not history:
        return history

    chronological_history = sorted(history, key=lambda row: row["date"])

    enriched_history: List[Dict[str, Any]] = []
    previous_row: Optional[Dict[str, Any]] = None

    for row in chronological_history:
        current_row = dict(row)

        if previous_row is None:
            current_row["comparison"] = {
                "value_change": 0.0,
                "return_change": 0.0,
                "drawdown_change": 0.0,
            }
        else:
            current_row["comparison"] = {
                "value_change": float(current_row["portfolio_value"] - previous_row["portfolio_value"]),
                "return_change": float(current_row["cumulative_return"] - previous_row["cumulative_return"]),
                "drawdown_change": float(current_row["drawdown"] - previous_row["drawdown"]),
            }

        enriched_history.append(current_row)
        previous_row = current_row

    return enriched_history


# =========================
# ROUTES
# =========================

@router.get("", response_model=PortfolioResponse)
def get_portfolio(
    persist_snapshot: bool = Query(True),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    if not _is_premium_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )

    user_id = _extract_user_id(current_user)

    ranking_service = SignalRankingService()
    portfolio_service = PortfolioEngineService()

    try:
        ranked_signals = ranking_service.get_ranked_signals(
            user_id=user_id,
            premium=True,
        )

        if ranked_signals is None:
            ranked_signals = []

        portfolio = portfolio_service.build_portfolio(
            user_id=user_id,
            ranked_signals=ranked_signals,
            persist_snapshot=persist_snapshot,
        )

        return portfolio

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio generation failed: {str(exc)}",
        ) from exc


@router.get("/performance", response_model=PortfolioPerformanceResponseSchema)
def get_portfolio_performance(
    force_recompute: bool = Query(False),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    user_id = _extract_user_id(current_user)
    is_premium = _is_premium_user(current_user)

    try:
        result = performance_adapter.get_performance_for_user(
            user_id=user_id,
            force_recompute=force_recompute,
        )

        if not is_premium:
            return _mask_free_performance_payload(result)

        return {
            "summary": result.summary,
            "signal_accuracy": result.signal_accuracy,
            "intelligence": result.intelligence,
            "meta": result.meta,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio performance failed: {str(exc)}",
        ) from exc


@router.get("/history", response_model=PortfolioHistoryResponseSchema)
def get_portfolio_history(
    limit: int = Query(24, ge=1, le=120),
    include_comparison: bool = Query(True),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    user_id = _extract_user_id(current_user)
    is_premium = _is_premium_user(current_user)

    try:
        result = performance_adapter.get_history_for_user(user_id=user_id)

        history = sorted(result.history, key=lambda row: row["date"])

        if is_premium:
            history = history[-limit:]
        else:
            history = history[-6:]

        if include_comparison:
            history = _add_snapshot_comparison(history)

        return {
            "history": history,
            "count": len(history),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio history failed: {str(exc)}",
        ) from exc