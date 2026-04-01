from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from auth.dependencies import get_current_user
from api.schemas.performance_schema import (
    PortfolioHistoryResponseSchema,
    PortfolioPerformanceResponseSchema,
)
from live.services.allocation_snapshot_service import AllocationSnapshotService
from services.portfolio_engine_service import PortfolioEngineService
from services.portfolio_performance_adapter import PortfolioPerformanceAdapter
from services.risk_adjusted_snapshot_service import RiskAdjustedSnapshotService
from services.risk_aware_portfolio_engine_service import RiskAwarePortfolioEngineService
from services.signal_ranking_service import SignalRankingService


router = APIRouter(prefix="/portfolio", tags=["portfolio"])

performance_adapter = PortfolioPerformanceAdapter()
portfolio_service = PortfolioEngineService()
risk_aware_engine = RiskAwarePortfolioEngineService()
risk_adjusted_snapshot_service = RiskAdjustedSnapshotService()
allocation_snapshot_service = AllocationSnapshotService()


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


def _convert_positions_to_allocations(portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
    theme_map = {
        "SPY": "equities",
        "QQQ": "equities",
        "IWM": "equities",
        "IEF": "duration",
        "TLT": "long_duration",
        "GLD": "commodities",
        "SHY": "cash",
        "CASH": "cash",
    }

    allocations: List[Dict[str, Any]] = []

    for position in portfolio.get("positions", []):
        symbol = position["symbol"]
        allocations.append(
            {
                "asset": symbol,
                "theme": theme_map.get(symbol, "other"),
                "weight": float(position["target_weight"]),
            }
        )

    return allocations


def _extract_current_drawdown(user_id: int) -> Optional[float]:
    try:
        result = performance_adapter.get_performance_for_user(
            user_id=user_id,
            force_recompute=False,
        )
        intelligence = getattr(result, "intelligence", None)
        if intelligence and isinstance(intelligence, dict):
            return float(intelligence.get("current_drawdown", 0.0))
        return 0.0
    except Exception:
        return None


def _persist_allocation_snapshot_to_db(
    user_id: int,
    portfolio_payload: Dict[str, Any],
) -> None:
    allocation_snapshot_service.persist_snapshot(
        user_id=user_id,
        portfolio=portfolio_payload,
    )


def _mask_free_performance_payload(result: Any) -> Dict[str, Any]:
    summary = result.summary

    if "base" in summary:
        summary = summary["base"]

    return {
        "summary": {
            "observations": summary["observations"],
            "total_return": summary["total_return"],
            "annualized_return": summary["annualized_return"],
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "latest_value": summary["latest_value"],
            "latest_period_return": summary["latest_period_return"],
            "latest_cumulative_return": summary["latest_cumulative_return"],
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


# =========================
# ROUTES
# =========================

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

        # 🔥 FIX HIER (korrekt eingerückt)
        summary = result.summary

        if isinstance(summary, dict) and "base" in summary:
            summary = summary["base"]

        return {
            "summary": summary,
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