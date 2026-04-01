from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class RiskOverlayConfigRequest(BaseModel):
    profile_name: str = Field(..., min_length=1)
    is_active: bool = True

    max_single_asset_weight: float = Field(0.35, ge=0.0, le=1.0)
    max_single_theme_weight: float = Field(0.60, ge=0.0, le=1.0)

    min_cash_weight: float = Field(0.00, ge=0.0, le=1.0)
    max_cash_weight: float = Field(1.00, ge=0.0, le=1.0)
    base_cash_weight: float = Field(0.00, ge=0.0, le=1.0)

    weak_signal_cash_scale: float = Field(0.25, ge=0.0, le=1.0)
    risk_off_cash_weight: float = Field(0.70, ge=0.0, le=1.0)
    risk_off_trigger: float = Field(0.80, ge=0.0, le=1.0)

    max_portfolio_leverage: float = Field(1.00, ge=0.0, le=2.0)
    redistribute_excess_to_cash: bool = True

    risk_off_defensive_asset: str = Field("SHY", min_length=1)
    cash_proxy_asset: str = Field("CASH", min_length=1)

    @model_validator(mode="after")
    def validate_ranges(self) -> "RiskOverlayConfigRequest":
        if self.min_cash_weight > self.max_cash_weight:
            raise ValueError("min_cash_weight must be <= max_cash_weight")
        if self.base_cash_weight > self.max_cash_weight:
            raise ValueError("base_cash_weight must be <= max_cash_weight")
        return self


class RiskOverlayConfigResponse(RiskOverlayConfigRequest):
    id: int
    created_at: str
    updated_at: str


class AssetAllocationInput(BaseModel):
    asset: str = Field(..., min_length=1)
    theme: str = Field(..., min_length=1)
    weight: float = Field(..., ge=0.0, le=1.0)

    @field_validator("asset", "theme")
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        return value.strip()


class RiskOverlayApplyRequest(BaseModel):
    signal_name: str = Field(..., min_length=1)
    regime_name: Optional[str] = None
    confidence_score: float = Field(0.50, ge=0.0, le=1.0)
    risk_score: float = Field(0.50, ge=0.0, le=1.0)
    profile_name: Optional[str] = None
    base_allocations: List[AssetAllocationInput]

    @model_validator(mode="after")
    def validate_base_allocations(self) -> "RiskOverlayApplyRequest":
        if not self.base_allocations:
            raise ValueError("base_allocations must not be empty")

        total_weight = round(sum(item.weight for item in self.base_allocations), 8)
        if total_weight <= 0:
            raise ValueError("base_allocations total weight must be > 0")
        return self


class RiskOverlayAdjustedAsset(BaseModel):
    asset: str
    theme: str
    base_weight: float
    adjusted_weight: float
    delta_weight: float


class RiskOverlaySummary(BaseModel):
    base_weight_sum: float
    adjusted_weight_sum: float
    cash_weight: float
    risk_off_triggered: bool
    applied_profile_name: str
    notes: List[str]


class RiskOverlayApplyResponse(BaseModel):
    signal_name: str
    regime_name: Optional[str]
    confidence_score: float
    risk_score: float
    summary: RiskOverlaySummary
    adjusted_allocations: List[RiskOverlayAdjustedAsset]
    theme_weights_before: Dict[str, float]
    theme_weights_after: Dict[str, float]