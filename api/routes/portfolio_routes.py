from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from services.portfolio_engine_service import PortfolioEngineService
from services.signal_ranking_service import SignalRankingService

from auth.dependencies import get_current_user


router = APIRouter(prefix="/portfolio", tags=["portfolio"])


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
    """
    Supports ORM objects + dicts
    """

    # ORM object (dein Fall)
    if hasattr(current_user, "subscription_tier"):
        return str(current_user.subscription_tier).lower() == "premium"

    if hasattr(current_user, "is_premium"):
        return current_user.is_premium is True

    # Dict fallback
    if isinstance(current_user, dict):
        if current_user.get("is_premium") is True:
            return True

        plan = str(current_user.get("plan", "")).lower()
        role = str(current_user.get("role", "")).lower()
        subscription = str(current_user.get("subscription_tier", "")).lower()

        return any(v == "premium" for v in [plan, role, subscription])

    return False


def _extract_user_id(current_user) -> int:
    # ORM object
    if hasattr(current_user, "id"):
        return int(current_user.id)

    # Dict fallback
    if isinstance(current_user, dict):
        user_id = current_user.get("id") or current_user.get("user_id")
        if user_id is not None:
            return int(user_id)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="User object does not contain an id/user_id field.",
    )


# =========================
# ROUTE
# =========================

@router.get("", response_model=PortfolioResponse)
def get_portfolio(
    persist_snapshot: bool = Query(True),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    # 🔐 Premium check
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