from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.signal_ranking_schema import (
    RankedSignalsFreeResponse,
    RankedSignalsPremiumResponse,
)
from auth.dependencies import get_current_active_user
from auth.dependencies import require_premium_user
from services.signal_ranking_service import SignalRankingService
from services.signal_service import SignalService


print("✅ signal_ranking_routes loaded")


router = APIRouter(prefix="/signals/ranked", tags=["signals-ranked"])


# =========================
# DEPENDENCIES
# =========================

def get_signal_service() -> SignalService:
    return SignalService()


def get_signal_ranking_service() -> SignalRankingService:
    return SignalRankingService()


# =========================
# CORE ADAPTER (YOUR FORMAT)
# =========================

def _extract_signal_list(raw_payload: Any) -> List[Dict[str, Any]]:
    """
    Converts your macro + signal dict into asset-based list
    """

    # =========================
    # YOUR CUSTOM FORMAT
    # =========================
    if isinstance(raw_payload, dict):

        macro = raw_payload.get("macro", {})
        signals = raw_payload.get("signals", {})

        if isinstance(signals, dict):

            confidence = signals.get("confidence", 0.5)
            regime = signals.get("regime")

            # Macro forecasts
            forecast_1m = macro.get("forecast_1m")
            forecast_3m = macro.get("forecast_3m")
            forecast_6m = macro.get("forecast_6m")
            cpi_yoy = macro.get("current_inflation")

            # Mapping → tradable assets
            asset_mapping = {
                "bond_signal": "TLT",
                "equity_signal": "SPY",
                "usd_signal": "UUP",
                "gold_signal": "GLD",
            }

            result: List[Dict[str, Any]] = []

            for signal_key, asset_name in asset_mapping.items():
                signal_value = signals.get(signal_key)

                if signal_value is None:
                    continue

                result.append(
                    {
                        "asset": asset_name,
                        "signal": signal_value,
                        "confidence": confidence,
                        "forecast_1m": forecast_1m,
                        "forecast_3m": forecast_3m,
                        "forecast_6m": forecast_6m,
                        "cpi_yoy": cpi_yoy,
                        "regime": regime,
                    }
                )

            if result:
                return result

    # =========================
    # FALLBACK FORMATS
    # =========================

    if isinstance(raw_payload, list):
        return [x for x in raw_payload if isinstance(x, dict)]

    if isinstance(raw_payload, dict):
        for key in ["signals", "assets", "data", "results"]:
            value = raw_payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    print("❌ Unsupported payload format:", raw_payload)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Signal payload format is not supported by ranking adapter.",
    )


# =========================
# SIGNAL LOADER
# =========================

def _load_raw_signals(signal_service: SignalService) -> List[Dict[str, Any]]:
    """
    Finds compatible method in SignalService
    """

    candidate_methods = [
        "get_signals",
        "get_live_signals",
        "generate_signals",
        "build_signals",
    ]

    for method_name in candidate_methods:
        method = getattr(signal_service, method_name, None)

        if callable(method):
            raw_payload = method()

            print(f"🔥 using method: {method_name}")
            print("🔥 raw payload:", raw_payload)

            return _extract_signal_list(raw_payload)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No supported signal loading method found on SignalService.",
    )


# =========================
# ROUTES
# =========================

@router.get(
    "/free",
    response_model=RankedSignalsFreeResponse,
    status_code=status.HTTP_200_OK,
)
def get_ranked_free_signals(
    signal_service: SignalService = Depends(get_signal_service),
    ranking_service: SignalRankingService = Depends(get_signal_ranking_service),
) -> RankedSignalsFreeResponse:

    print("🔥 /signals/ranked/free called")

    raw_signals = _load_raw_signals(signal_service)

    ranked = ranking_service.rank_signals(
        raw_signals=raw_signals,
        top_n=2,
        premium=False,
    )

    return RankedSignalsFreeResponse(**ranked)


@router.get(
    "/premium",
    response_model=RankedSignalsPremiumResponse,
    status_code=status.HTTP_200_OK,
)
def get_ranked_premium_signals(
    _current_user=Depends(require_premium_user),
    signal_service: SignalService = Depends(get_signal_service),
    ranking_service: SignalRankingService = Depends(get_signal_ranking_service),
) -> RankedSignalsPremiumResponse:

    print("🔥 /signals/ranked/premium called")

    raw_signals = _load_raw_signals(signal_service)

    ranked = ranking_service.rank_signals(
        raw_signals=raw_signals,
        top_n=None,
        premium=True,
    )

    return RankedSignalsPremiumResponse(**ranked)