from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas.risk_score_schema import (
    RiskScoreConfigRequest,
    RiskScoreConfigResponse,
)
from live.repository.risk_score_config_repository import RiskScoreConfigRepository


router = APIRouter(prefix="/risk-score", tags=["risk-score"])

repository = RiskScoreConfigRepository()


@router.get("/config/active", response_model=RiskScoreConfigResponse)
def get_active_risk_score_config() -> RiskScoreConfigResponse:
    config = repository.get_active_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No active risk score config found.")
    return RiskScoreConfigResponse(**config)


@router.post("/config", response_model=RiskScoreConfigResponse)
def upsert_risk_score_config(payload: RiskScoreConfigRequest) -> RiskScoreConfigResponse:
    saved = repository.upsert_config(payload.model_dump())
    return RiskScoreConfigResponse(**saved)