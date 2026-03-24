from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from auth.jwt_handler import decode_access_token
from auth.repositories.user_repository import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_repository() -> UserRepository:
    return UserRepository()


# =========================
# BASE USER
# =========================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    # -------------------------
    # Decode JWT
    # -------------------------
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # -------------------------
    # Extract & validate user_id
    # -------------------------
    user_id_raw = payload.get("sub")

    if user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id: int = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # -------------------------
    # Load user from DB
    # -------------------------
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# =========================
# ACTIVE USER
# =========================

def get_current_active_user(user=Depends(get_current_user)):
    if hasattr(user, "is_active") and user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


# =========================
# 🔥 PREMIUM PAYWALL
# =========================

def require_premium_user(user=Depends(get_current_active_user)):
    """
    Monetization Layer
    """

    # flexible support for multiple schemas
    user_plan = (
        getattr(user, "subscription_tier", None)
        or getattr(user, "plan", None)
        or getattr(user, "subscription", None)
    )

    if user_plan != "premium":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Premium subscription required",
                "upgrade_required": True,
                "features_locked": [
                    "full_ranking",
                    "allocation_strategy",
                    "alpha_layer",
                    "macro_forecasts",
                ],
            },
        )

    return user