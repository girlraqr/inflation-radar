from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from live.repository.allocation_repository import AllocationRepository
from live.repository.performance_repository import PortfolioPerformanceRepository
from services.performance_engine_service import PerformanceEngineService


@dataclass
class PortfolioPerformanceAdapterResult:
    summary: dict[str, Any]
    history: list[dict[str, Any]]
    signal_accuracy: dict[str, Any]
    intelligence: dict[str, Any]
    meta: dict[str, Any]
    alpha_intelligence: dict[str, Any]  # 🔥 NEU


class PortfolioPerformanceAdapter:
    def __init__(self) -> None:
        self.allocation_repository = AllocationRepository()
        self.performance_repository = PortfolioPerformanceRepository()

        self.performance_engine = PerformanceEngineService()

    # ---------------------------------------------------
    # MAIN PERFORMANCE
    # ---------------------------------------------------

    def get_performance_for_user(
        self,
        user_id: int,
        force_recompute: bool = False,
    ) -> PortfolioPerformanceAdapterResult:

        if not force_recompute:
            db_payload = self.performance_repository.get_latest_summary_payload(
                user_id=user_id
            )

            if db_payload is not None:
                return PortfolioPerformanceAdapterResult(
                    summary=db_payload["summary"],
                    history=[],
                    signal_accuracy=db_payload["signal_accuracy"],
                    intelligence=db_payload["intelligence"],
                    meta=db_payload["meta"],
                    alpha_intelligence=db_payload.get("alpha_intelligence", {}),  # 🔥 NEU
                )

        result = self.performance_engine.build_performance(
            user_id=user_id
        )

        return PortfolioPerformanceAdapterResult(
            summary=result.summary,
            history=result.history,
            signal_accuracy=result.signal_accuracy,
            intelligence=result.intelligence,
            meta=result.meta,
            alpha_intelligence=result.alpha_intelligence,  # 🔥 NEU
        )

    # ---------------------------------------------------
    # HISTORY
    # ---------------------------------------------------

    def get_history_for_user(
        self,
        user_id: int,
    ) -> PortfolioPerformanceAdapterResult:

        result = self.performance_engine.build_performance(
            user_id=user_id
        )

        return PortfolioPerformanceAdapterResult(
            summary=result.summary,
            history=result.history,
            signal_accuracy=result.signal_accuracy,
            intelligence=result.intelligence,
            meta=result.meta,
            alpha_intelligence=result.alpha_intelligence,  # 🔥 NEU
        )