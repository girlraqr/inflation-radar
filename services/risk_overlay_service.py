from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Dict, List

from api.schemas.risk_overlay_schema import (
    AssetAllocationInput,
    RiskOverlayAdjustedAsset,
    RiskOverlayApplyResponse,
    RiskOverlayConfigRequest,
    RiskOverlaySummary,
)


class RiskOverlayService:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _normalize_weights(items: List[dict]) -> List[dict]:
        total = sum(item["weight"] for item in items)
        if total <= 0:
            raise ValueError("Allocation sum must be > 0.")
        normalized = deepcopy(items)
        for item in normalized:
            item["weight"] = item["weight"] / total
        return normalized

    @staticmethod
    def _group_theme_weights(items: List[dict]) -> Dict[str, float]:
        theme_weights: Dict[str, float] = defaultdict(float)
        for item in items:
            theme_weights[item["theme"]] += item["weight"]
        return {key: round(value, 8) for key, value in theme_weights.items()}

    @staticmethod
    def _redistribute_within_theme(
        items: List[dict],
        theme: str,
        freed_weight: float,
        max_single_asset_weight: float,
    ) -> float:
        """
        Redistribute freed weight within the same theme to uncapped assets first.
        Returns remaining weight that could not be redistributed.
        """
        if freed_weight <= 0:
            return 0.0

        candidates = [
            item for item in items
            if item["theme"] == theme and item["weight"] < max_single_asset_weight
        ]
        if not candidates:
            return freed_weight

        remaining_capacity = sum(max_single_asset_weight - item["weight"] for item in candidates)
        if remaining_capacity <= 0:
            return freed_weight

        for item in candidates:
            capacity = max_single_asset_weight - item["weight"]
            share = freed_weight * (capacity / remaining_capacity)
            item["weight"] += share

        return 0.0

    def _apply_asset_caps(
        self,
        items: List[dict],
        config: RiskOverlayConfigRequest,
        notes: List[str],
    ) -> float:
        excess_to_cash = 0.0
        max_asset = config.max_single_asset_weight

        for item in items:
            if item["weight"] > max_asset:
                excess = item["weight"] - max_asset
                item["weight"] = max_asset
                leftover = self._redistribute_within_theme(
                    items=items,
                    theme=item["theme"],
                    freed_weight=excess,
                    max_single_asset_weight=max_asset,
                )
                excess_to_cash += leftover

        if excess_to_cash > 0:
            notes.append(
                f"Asset cap applied; {round(excess_to_cash, 6)} excess weight moved to cash."
            )
        return excess_to_cash

    def _apply_theme_caps(
        self,
        items: List[dict],
        config: RiskOverlayConfigRequest,
        notes: List[str],
    ) -> float:
        excess_to_cash = 0.0
        theme_weights = self._group_theme_weights(items)

        for theme, theme_weight in theme_weights.items():
            if theme_weight <= config.max_single_theme_weight:
                continue

            excess = theme_weight - config.max_single_theme_weight
            theme_items = [item for item in items if item["theme"] == theme]
            if not theme_items:
                continue

            total_theme_weight = sum(item["weight"] for item in theme_items)
            if total_theme_weight <= 0:
                continue

            for item in theme_items:
                reduction = excess * (item["weight"] / total_theme_weight)
                item["weight"] -= reduction

            excess_to_cash += excess

        if excess_to_cash > 0:
            notes.append(
                f"Theme cap applied; {round(excess_to_cash, 6)} excess weight moved to cash."
            )
        return excess_to_cash

    @staticmethod
    def _compute_dynamic_cash_target(
        confidence_score: float,
        risk_score: float,
        config: RiskOverlayConfigRequest,
    ) -> float:
        confidence_penalty = (1.0 - confidence_score) * config.weak_signal_cash_scale
        risk_penalty = risk_score * config.weak_signal_cash_scale
        cash_target = config.base_cash_weight + confidence_penalty + risk_penalty
        cash_target = max(config.min_cash_weight, cash_target)
        cash_target = min(config.max_cash_weight, cash_target)
        return cash_target

    @staticmethod
    def _shrink_risk_assets_pro_rata(items: List[dict], target_reduction: float) -> float:
        risky_total = sum(item["weight"] for item in items if item["asset"] != "CASH")
        if risky_total <= 0 or target_reduction <= 0:
            return 0.0

        target_reduction = min(target_reduction, risky_total)

        for item in items:
            if item["asset"] == "CASH":
                continue
            reduction = target_reduction * (item["weight"] / risky_total)
            item["weight"] -= reduction

        return target_reduction

    @staticmethod
    def _ensure_cash_asset(items: List[dict], cash_asset: str) -> None:
        existing = next((item for item in items if item["asset"] == cash_asset), None)
        if existing is None:
            items.append(
                {
                    "asset": cash_asset,
                    "theme": "cash",
                    "weight": 0.0,
                }
            )

    def apply_overlay(
        self,
        signal_name: str,
        regime_name: str | None,
        confidence_score: float,
        risk_score: float,
        base_allocations: List[AssetAllocationInput],
        config: RiskOverlayConfigRequest,
    ) -> RiskOverlayApplyResponse:
        notes: List[str] = []

        base_items = [
            {"asset": item.asset, "theme": item.theme, "weight": item.weight}
            for item in base_allocations
        ]
        base_items = self._normalize_weights(base_items)

        theme_weights_before = self._group_theme_weights(base_items)

        adjusted_items = deepcopy(base_items)
        self._ensure_cash_asset(adjusted_items, config.cash_proxy_asset)

        risk_off_triggered = risk_score >= config.risk_off_trigger

        if risk_off_triggered:
            notes.append("Risk-off trigger activated.")
            reduced = self._shrink_risk_assets_pro_rata(
                adjusted_items,
                config.risk_off_cash_weight,
            )
            cash_item = next(item for item in adjusted_items if item["asset"] == config.cash_proxy_asset)
            cash_item["weight"] += reduced
            notes.append(f"Risk-off moved {round(reduced, 6)} into cash.")
        else:
            asset_cap_excess = self._apply_asset_caps(adjusted_items, config, notes)
            theme_cap_excess = self._apply_theme_caps(adjusted_items, config, notes)

            if config.redistribute_excess_to_cash:
                cash_item = next(item for item in adjusted_items if item["asset"] == config.cash_proxy_asset)
                cash_item["weight"] += asset_cap_excess + theme_cap_excess

            dynamic_cash_target = self._compute_dynamic_cash_target(
                confidence_score=confidence_score,
                risk_score=risk_score,
                config=config,
            )

            current_cash = sum(
                item["weight"] for item in adjusted_items if item["asset"] == config.cash_proxy_asset
            )

            required_extra_cash = max(0.0, dynamic_cash_target - current_cash)
            if required_extra_cash > 0:
                moved = self._shrink_risk_assets_pro_rata(adjusted_items, required_extra_cash)
                cash_item = next(item for item in adjusted_items if item["asset"] == config.cash_proxy_asset)
                cash_item["weight"] += moved
                notes.append(f"Dynamic cash control moved {round(moved, 6)} into cash.")

        adjusted_items = self._normalize_weights(adjusted_items)

        theme_weights_after = self._group_theme_weights(adjusted_items)

        adjusted_allocations: List[RiskOverlayAdjustedAsset] = []
        base_lookup = {(item["asset"], item["theme"]): item["weight"] for item in base_items}

        for item in adjusted_items:
            base_weight = base_lookup.get((item["asset"], item["theme"]), 0.0)
            adjusted_weight = item["weight"]
            adjusted_allocations.append(
                RiskOverlayAdjustedAsset(
                    asset=item["asset"],
                    theme=item["theme"],
                    base_weight=round(base_weight, 8),
                    adjusted_weight=round(adjusted_weight, 8),
                    delta_weight=round(adjusted_weight - base_weight, 8),
                )
            )

        cash_weight = next(
            (allocation.adjusted_weight for allocation in adjusted_allocations if allocation.asset == config.cash_proxy_asset),
            0.0,
        )

        return RiskOverlayApplyResponse(
            signal_name=signal_name,
            regime_name=regime_name,
            confidence_score=round(confidence_score, 6),
            risk_score=round(risk_score, 6),
            summary=RiskOverlaySummary(
                base_weight_sum=round(sum(item["weight"] for item in base_items), 8),
                adjusted_weight_sum=round(sum(item.adjusted_weight for item in adjusted_allocations), 8),
                cash_weight=round(cash_weight, 8),
                risk_off_triggered=risk_off_triggered,
                applied_profile_name=config.profile_name,
                notes=notes,
            ),
            adjusted_allocations=adjusted_allocations,
            theme_weights_before=theme_weights_before,
            theme_weights_after=theme_weights_after,
        )