# services/portfolio_engine_service.py

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.signal_asset_mapping_service import SignalAssetMappingService

DEFAULT_DB_PATH = "storage/app.db"


@dataclass
class PortfolioSignal:
    symbol: str
    score: float
    confidence: float
    direction: str = "long"
    forecast: Optional[float] = None
    asset_name: Optional[str] = None
    asset_class: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PortfolioPosition:
    symbol: str
    target_weight: float
    current_weight: float
    delta: float
    score: float
    confidence: float
    direction: str
    forecast: Optional[float]
    asset_name: Optional[str]
    asset_class: Optional[str]
    action: str


@dataclass
class PortfolioSnapshot:
    user_id: int
    generated_at: str
    rebalance_required: bool
    rebalance_reason: str
    total_invested_weight: float
    cash_weight: float
    allocation_hint: str
    positions: List[Dict[str, Any]]
    meta: Dict[str, Any]


class PortfolioEngineService:

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        max_positions: int = 6,
        min_position_weight: float = 0.05,
        max_position_weight: float = 0.35,
        rebalance_drift_threshold: float = 0.05,
        min_score_threshold: float = 0.0,
        reserve_cash_floor: float = 0.00,
        reserve_cash_ceiling: float = 0.25,
        score_power: float = 1.30,
        confidence_power: float = 1.10,
    ) -> None:
        self.db_path = db_path
        self.max_positions = max_positions
        self.min_position_weight = min_position_weight
        self.max_position_weight = max_position_weight
        self.rebalance_drift_threshold = rebalance_drift_threshold
        self.min_score_threshold = min_score_threshold
        self.reserve_cash_floor = reserve_cash_floor
        self.reserve_cash_ceiling = reserve_cash_ceiling
        self.score_power = score_power
        self.confidence_power = confidence_power

        self.signal_asset_mapping_service = SignalAssetMappingService()

        self._ensure_tables()

    # ---------------------------------------------------
    # MAIN
    # ---------------------------------------------------

    def build_portfolio(
        self,
        user_id: int,
        ranked_signals: List[Dict[str, Any]],
        regime: Optional[str] = None,
        persist_snapshot: bool = True,
    ) -> Dict[str, Any]:

        normalized_signals = self._normalize_signals(ranked_signals)
        eligible_signals = self._filter_eligible_signals(normalized_signals)

        if not eligible_signals:
            snapshot = PortfolioSnapshot(
                user_id=user_id,
                generated_at=self._utcnow_iso(),
                rebalance_required=False,
                rebalance_reason="no_eligible_signals",
                total_invested_weight=0.0,
                cash_weight=1.0,
                allocation_hint="DEFENSIVE_CASH",
                positions=[],
                meta={
                    "engine_version": "2.0.0",
                    "eligible_signal_count": 0,
                    "raw_signal_count": len(ranked_signals),
                },
            )
            if persist_snapshot:
                self._save_snapshot(snapshot)
            return asdict(snapshot)

        selected_signals = eligible_signals[: self.max_positions]

        # 🔥 Mapping Layer
        mapping_input = [
            {
                "signal": s.symbol,
                "conviction": s.confidence,
                "score": s.score,
            }
            for s in selected_signals
        ]

        mapping_result = self.signal_asset_mapping_service.map_signals_to_assets(
            signals=mapping_input,
            regime=regime,
            top_n=self.max_positions,
        )

        mapped_weights = mapping_result["weights"]

        mapped_signals: List[PortfolioSignal] = []

        for symbol, weight in mapped_weights.items():
            mapped_signals.append(
                PortfolioSignal(
                    symbol=symbol,
                    score=weight,
                    confidence=1.0,
                    direction="long",
                    forecast=None,
                    asset_name=None,
                    asset_class="mapped",
                    metadata={"source": "mapping_layer"},
                )
            )

        target_weights, reserve_cash = self._compute_target_weights(mapped_signals)

        previous_snapshot = self._load_latest_snapshot(user_id=user_id)
        current_weights = self._extract_current_weights(previous_snapshot)

        positions, rebalance_required, rebalance_reason = self._build_positions(
            signals=mapped_signals,
            target_weights=target_weights,
            current_weights=current_weights,
        )

        total_invested_weight = round(sum(p.target_weight for p in positions), 6)
        cash_weight = round(max(0.0, 1.0 - total_invested_weight), 6)

        allocation_hint = self._build_allocation_hint(positions, cash_weight)

        snapshot = PortfolioSnapshot(
            user_id=user_id,
            generated_at=self._utcnow_iso(),
            rebalance_required=rebalance_required,
            rebalance_reason=rebalance_reason,
            total_invested_weight=total_invested_weight,
            cash_weight=cash_weight if cash_weight > 0 else reserve_cash,
            allocation_hint=allocation_hint,
            positions=[asdict(p) for p in positions],
            meta={
                "engine_version": "2.0.0",
                "regime": mapping_result["regime"],
                "mapping_breakdown": mapping_result["mapping_breakdown"],
                "eligible_signal_count": len(eligible_signals),
                "selected_signal_count": len(selected_signals),
                "raw_signal_count": len(ranked_signals),
                "max_positions": self.max_positions,
            },
        )

        if persist_snapshot:
            self._save_snapshot(snapshot)

        return asdict(snapshot)

    # ---------------------------------------------------
    # 🔥 FIX
    # ---------------------------------------------------

    def _build_allocation_hint(self, positions, cash_weight: float) -> str:
        if not positions:
            return "DEFENSIVE_CASH"

        invested_positions = [p for p in positions if p.target_weight > 0]

        if not invested_positions:
            return "DEFENSIVE_CASH"

        avg_confidence = sum(p.confidence for p in invested_positions) / len(invested_positions)
        max_weight = max(p.target_weight for p in invested_positions)

        if cash_weight >= 0.20:
            return "CAUTIOUS_RISK_ON"

        if avg_confidence >= 0.75 and max_weight <= 0.25:
            return "BALANCED_GROWTH"

        if avg_confidence >= 0.75:
            return "HIGH_CONVICTION"

        return "MODERATE_RISK"

    # ---------------------------------------------------
    # EXISTING LOGIC (unchanged)
    # ---------------------------------------------------

    def _normalize_signals(self, ranked_signals: List[Dict[str, Any]]) -> List[PortfolioSignal]:
        results: List[PortfolioSignal] = []

        for item in ranked_signals:
            symbol = item.get("symbol") or item.get("name")
            if not symbol:
                continue

            results.append(
                PortfolioSignal(
                    symbol=str(symbol),
                    score=float(item.get("score", 0)),
                    confidence=float(item.get("confidence", 0.5)),
                )
            )

        return results

    def _filter_eligible_signals(self, signals: List[PortfolioSignal]) -> List[PortfolioSignal]:
        return [s for s in signals if s.score > 0 and s.confidence > 0]

    def _compute_target_weights(self, signals: List[PortfolioSignal]):
        strengths = {s.symbol: s.score for s in signals}
        total = sum(strengths.values()) or 1
        weights = {k: v / total for k, v in strengths.items()}
        return weights, 0.0

    def _build_positions(self, signals, target_weights, current_weights):
        positions = []

        for s in signals:
            positions.append(
                PortfolioPosition(
                    symbol=s.symbol,
                    target_weight=target_weights.get(s.symbol, 0),
                    current_weight=current_weights.get(s.symbol, 0),
                    delta=0,
                    score=s.score,
                    confidence=s.confidence,
                    direction=s.direction,
                    forecast=None,
                    asset_name=None,
                    asset_class=s.asset_class,
                    action="HOLD",
                )
            )

        return positions, False, "none"

    # ---------------------------------------------------
    # DB
    # ---------------------------------------------------

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                generated_at TEXT,
                snapshot_json TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO portfolio_snapshots (user_id, generated_at, snapshot_json) VALUES (?, ?, ?)",
            (snapshot.user_id, snapshot.generated_at, json.dumps(asdict(snapshot))),
        )
        conn.commit()
        conn.close()

    def _load_latest_snapshot(self, user_id: int) -> Optional[Dict[str, Any]]:
        return None

    def _extract_current_weights(self, snapshot: Optional[Dict[str, Any]]) -> Dict[str, float]:
        return {}

    def _utcnow_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()