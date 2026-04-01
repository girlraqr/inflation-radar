from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas.risk_overlay_schema import (
    RiskOverlayApplyRequest,
    RiskOverlayApplyResponse,
    RiskOverlayConfigRequest,
    RiskOverlayConfigResponse,
)
from live.repository.risk_overlay_repository import RiskOverlayRepository
from services.risk_overlay_service import RiskOverlayService


router = APIRouter(prefix="/risk-overlay", tags=["risk-overlay"])

repository = RiskOverlayRepository()
service = RiskOverlayService()


@router.get("/config/active", response_model=RiskOverlayConfigResponse)
def get_active_risk_overlay_config() -> RiskOverlayConfigResponse:
    config = repository.get_active_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No active risk overlay config found.")
    return RiskOverlayConfigResponse(**config)


@router.post("/config", response_model=RiskOverlayConfigResponse)
def upsert_risk_overlay_config(payload: RiskOverlayConfigRequest) -> RiskOverlayConfigResponse:
    saved = repository.upsert_config(payload.model_dump())
    return RiskOverlayConfigResponse(**saved)


@router.post("/apply", response_model=RiskOverlayApplyResponse)
def apply_risk_overlay(payload: RiskOverlayApplyRequest) -> RiskOverlayApplyResponse:
    config_dict = (
        repository.get_config_by_profile(payload.profile_name)
        if payload.profile_name
        else repository.get_active_config()
    )

    if config_dict is None:
        raise HTTPException(status_code=404, detail="Risk overlay config not found.")

    config = RiskOverlayConfigRequest(**config_dict)

    return service.apply_overlay(
        signal_name=payload.signal_name,
        regime_name=payload.regime_name,
        confidence_score=payload.confidence_score,
        risk_score=payload.risk_score,
        base_allocations=payload.base_allocations,
        config=config,
    )