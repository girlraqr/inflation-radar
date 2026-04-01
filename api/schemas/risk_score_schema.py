from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RiskScoreConfigRequest(BaseModel):
    profile_name: str = Field(..., min_length=1)
    is_active: bool = True

    confidence_weight_strength: float = Field(0.50, ge=0.0, le=2.0)
    confidence_weight_agreement: float = Field(0.25, ge=0.0, le=2.0)
    confidence_weight_breadth: float = Field(0.25, ge=0.0, le=2.0)

    risk_weight_inverse_strength: float = Field(0.35, ge=0.0, le=2.0)
    risk_weight_dispersion: float = Field(0.20, ge=0.0, le=2.0)
    risk_weight_concentration: float = Field(0.30, ge=0.0, le=2.0)
    risk_weight_drawdown: float = Field(0.15, ge=0.0, le=2.0)

    breadth_full_score_at: int = Field(5, ge=1, le=50)
    drawdown_full_penalty_at: float = Field(0.20, ge=0.01, le=1.0)

    @model_validator(mode="after")
    def validate_weight_groups(self) -> "RiskScoreConfigRequest":
        confidence_total = (
            self.confidence_weight_strength
            + self.confidence_weight_agreement
            + self.confidence_weight_breadth
        )
        risk_total = (
            self.risk_weight_inverse_strength
            + self.risk_weight_dispersion
            + self.risk_weight_concentration
            + self.risk_weight_drawdown
        )

        if confidence_total <= 0:
            raise ValueError("Confidence weights must sum to > 0.")

        if risk_total <= 0:
            raise ValueError("Risk weights must sum to > 0.")

        return self


class RiskScoreConfigResponse(RiskScoreConfigRequest):
    id: int
    created_at: str
    updated_at: str