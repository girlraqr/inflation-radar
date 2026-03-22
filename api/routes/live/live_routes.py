from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.schemas.live_schema import (
    LiveHistoryItemSchema,
    LiveSignalResponseSchema,
    LiveStatusResponseSchema,
)
from live.services.live_signal_service import LiveSignalService

router = APIRouter(prefix="/live", tags=["live"])
live_signal_service = LiveSignalService()


@router.get("/current", response_model=LiveSignalResponseSchema)
def get_current_live_signal():
    payload = live_signal_service.get_current_signal()
    if not payload:
        raise HTTPException(status_code=404, detail="Kein Live-Signal verfügbar.")
    return payload


@router.get("/allocation/current")
def get_current_allocation():
    payload = live_signal_service.get_current_allocation()
    if not payload:
        raise HTTPException(status_code=404, detail="Keine aktuelle Allocation verfügbar.")
    return payload


@router.get("/regime/current")
def get_current_regime():
    payload = live_signal_service.get_current_regime()
    if not payload:
        raise HTTPException(status_code=404, detail="Kein aktuelles Regime verfügbar.")
    return payload


@router.get("/status", response_model=LiveStatusResponseSchema)
def get_live_status():
    payload = live_signal_service.get_status()
    if not payload:
        raise HTTPException(status_code=404, detail="Kein Live-Status verfügbar.")
    return payload


@router.get("/history", response_model=list[LiveHistoryItemSchema])
def get_live_history(limit: int = Query(default=20, ge=1, le=200)):
    return live_signal_service.get_history(limit=limit)


@router.post("/refresh", response_model=LiveSignalResponseSchema)
def refresh_live_signal():
    """
    Für den Start praktisch.
    Später mit Auth absichern oder nur intern nutzen.
    """
    return live_signal_service.build_and_publish_live_signal()