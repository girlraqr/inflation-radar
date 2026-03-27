from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

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


class PortfolioPerformanceAdapter:
    def __init__(self) -> None:
        self.allocation_repository = AllocationRepository()
        self.performance_repository = PortfolioPerformanceRepository()
        self.performance_engine = PerformanceEngineService(repository=self.performance_repository)

    def get_performance_for_user(
        self,
        user_id: int,
        force_recompute: bool = False,
    ) -> PortfolioPerformanceAdapterResult:
        if not force_recompute:
            db_payload = self.performance_repository.get_latest_summary_payload(user_id=user_id)
            if db_payload is not None:
                return PortfolioPerformanceAdapterResult(
                    summary=db_payload["summary"],
                    history=[],
                    signal_accuracy=db_payload["signal_accuracy"],
                    intelligence=db_payload["intelligence"],
                    meta=db_payload["meta"],
                )

        allocation_snapshots = self._load_allocation_snapshots(user_id)
        asset_returns = self._load_asset_returns()
        signal_history = self._load_signal_history()

        result = self.performance_engine.build_performance(
            user_id=user_id,
            allocation_snapshots=allocation_snapshots,
            asset_returns=asset_returns,
            signal_history=signal_history,
            starting_value=100.0,
        )

        return PortfolioPerformanceAdapterResult(
            summary=result.summary,
            history=result.history,
            signal_accuracy=result.signal_accuracy,
            intelligence=result.intelligence,
            meta={"source": "computed"},
        )

    def get_history_for_user(
        self,
        user_id: int,
    ) -> PortfolioPerformanceAdapterResult:
        allocation_snapshots = self._load_allocation_snapshots(user_id)
        asset_returns = self._load_asset_returns()
        signal_history = self._load_signal_history()

        result = self.performance_engine.build_performance(
            user_id=user_id,
            allocation_snapshots=allocation_snapshots,
            asset_returns=asset_returns,
            signal_history=signal_history,
            starting_value=100.0,
        )

        return PortfolioPerformanceAdapterResult(
            summary=result.summary,
            history=result.history,
            signal_accuracy=result.signal_accuracy,
            intelligence=result.intelligence,
            meta={"source": "computed"},
        )

    def _load_allocation_snapshots(self, user_id: int) -> pd.DataFrame:
        rows = self.allocation_repository.get_user_snapshots(user_id=user_id)
        return pd.DataFrame(rows)

    def _load_asset_returns(self) -> pd.DataFrame:
        df = pd.read_csv("storage/cache/asset_returns.csv")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")

    def _load_signal_history(self) -> pd.DataFrame:
        try:
            return pd.read_csv("storage/cache/signal_history.csv")
        except FileNotFoundError:
            return pd.DataFrame()