from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.schemas.risk_overlay_schema import (
    AssetAllocationInput,
    RiskOverlayApplyResponse,
    RiskOverlayConfigRequest,
)
from live.repository.risk_overlay_repository import RiskOverlayRepository
from services.risk_overlay_service import RiskOverlayService
from services.risk_score_engine_service import RiskScoreEngineService


class RiskAwarePortfolioEngineService:
    """
    Additiver Wrapper:
    - nimmt bestehendes Base-Portfolio
    - berechnet automatisch confidence_score + risk_score, falls nicht mitgegeben
    - wendet danach den Risk Overlay an
    """

    def __init__(
        self,
        risk_overlay_service: Optional[RiskOverlayService] = None,
        risk_overlay_repository: Optional[RiskOverlayRepository] = None,
        risk_score_engine_service: Optional[RiskScoreEngineService] = None,
    ) -> None:
        self.risk_overlay_service = risk_overlay_service or RiskOverlayService()
        self.risk_overlay_repository = risk_overlay_repository or RiskOverlayRepository()
        self.risk_score_engine_service = risk_score_engine_service or RiskScoreEngineService()

    def apply_risk_overlay_to_portfolio(
        self,
        base_portfolio_payload: Dict[str, Any],
        profile_name: str | None = None,
        ranked_signals: Optional[List[Any]] = None,
        current_drawdown: Optional[float] = None,
    ) -> Dict[str, Any]:
        signal_name = base_portfolio_payload["signal_name"]
        regime_name = base_portfolio_payload.get("regime_name")

        allocations_raw: List[Dict[str, Any]] = base_portfolio_payload["allocations"]
        base_allocations = [
            AssetAllocationInput(
                asset=item["asset"],
                theme=item["theme"],
                weight=float(item["weight"]),
            )
            for item in allocations_raw
        ]

        score_result = self.risk_score_engine_service.calculate_scores(
            ranked_signals=ranked_signals,
            portfolio={
                "positions": [
                    {
                        "target_weight": float(item["weight"]),
                        "symbol": item["asset"],
                    }
                    for item in allocations_raw
                ]
            },
            current_drawdown=current_drawdown,
        )

        confidence_score = float(
            base_portfolio_payload.get("confidence_score", score_result["confidence_score"])
        )
        risk_score = float(
            base_portfolio_payload.get("risk_score", score_result["risk_score"])
        )

        config_dict = (
            self.risk_overlay_repository.get_config_by_profile(profile_name)
            if profile_name
            else self.risk_overlay_repository.get_active_config()
        )

        if config_dict is None:
            config_dict = {
                "profile_name": "in_memory_default",
                "is_active": True,
                "max_single_asset_weight": 0.35,
                "max_single_theme_weight": 0.60,
                "min_cash_weight": 0.00,
                "max_cash_weight": 1.00,
                "base_cash_weight": 0.00,
                "weak_signal_cash_scale": 0.25,
                "risk_off_cash_weight": 0.70,
                "risk_off_trigger": 0.80,
                "max_portfolio_leverage": 1.00,
                "redistribute_excess_to_cash": True,
                "risk_off_defensive_asset": "SHY",
                "cash_proxy_asset": "CASH",
            }

        config = RiskOverlayConfigRequest(**config_dict)

        overlay_result: RiskOverlayApplyResponse = self.risk_overlay_service.apply_overlay(
            signal_name=signal_name,
            regime_name=regime_name,
            confidence_score=confidence_score,
            risk_score=risk_score,
            base_allocations=base_allocations,
            config=config,
        )

        return {
            "overlay": overlay_result.model_dump(),
            "risk_engine": score_result,
        }