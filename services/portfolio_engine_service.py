# services/portfolio_engine_service.py

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


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
    action: str  # BUY / SELL / HOLD / EXIT / NEW


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
    """
    Premium Portfolio Engine:
    - score + confidence based allocation
    - caps / floors
    - cash reserve
    - rebalance detection
    - snapshot persistence in SQLite
    """

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

        self._ensure_tables()

    # -----------------------------
    # Public API
    # -----------------------------

    def build_portfolio(
        self,
        user_id: int,
        ranked_signals: List[Dict[str, Any]],
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
                    "engine_version": "1.0.0",
                    "eligible_signal_count": 0,
                    "raw_signal_count": len(ranked_signals),
                },
            )
            if persist_snapshot:
                self._save_snapshot(snapshot)
            return asdict(snapshot)

        selected_signals = eligible_signals[: self.max_positions]
        target_weights, reserve_cash = self._compute_target_weights(selected_signals)

        previous_snapshot = self._load_latest_snapshot(user_id=user_id)
        current_weights = self._extract_current_weights(previous_snapshot)

        positions, rebalance_required, rebalance_reason = self._build_positions(
            signals=selected_signals,
            target_weights=target_weights,
            current_weights=current_weights,
        )

        total_invested_weight = round(sum(p.target_weight for p in positions), 6)
        cash_weight = round(max(0.0, 1.0 - total_invested_weight), 6)
        allocation_hint = self._build_allocation_hint(positions=positions, cash_weight=cash_weight)

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
                "engine_version": "1.0.0",
                "eligible_signal_count": len(eligible_signals),
                "selected_signal_count": len(selected_signals),
                "raw_signal_count": len(ranked_signals),
                "max_positions": self.max_positions,
                "rebalance_drift_threshold": self.rebalance_drift_threshold,
                "min_position_weight": self.min_position_weight,
                "max_position_weight": self.max_position_weight,
            },
        )

        if persist_snapshot:
            self._save_snapshot(snapshot)

        return asdict(snapshot)

    # -----------------------------
    # Normalization
    # -----------------------------

    def _normalize_signals(self, ranked_signals: List[Dict[str, Any]]) -> List[PortfolioSignal]:
        results: List[PortfolioSignal] = []

        for item in ranked_signals:
            symbol = self._first_non_empty(
                item.get("symbol"),
                item.get("ticker"),
                item.get("series_id"),
                item.get("id"),
                item.get("name"),
            )
            if not symbol:
                continue

            raw_score = self._safe_float(
                self._first_non_empty(
                    item.get("score"),
                    item.get("final_score"),
                    item.get("premium_score"),
                    item.get("ranking_score"),
                    item.get("teaser_score"),
                ),
                default=0.0,
            )

            raw_confidence = self._safe_float(
                self._first_non_empty(
                    item.get("confidence"),
                    item.get("model_confidence"),
                    item.get("probability"),
                    item.get("signal_confidence"),
                ),
                default=0.5,
            )

            confidence = self._normalize_confidence(raw_confidence)

            forecast = self._safe_float(item.get("forecast"), default=None)
            direction = str(item.get("direction", "long")).lower().strip() or "long"

            results.append(
                PortfolioSignal(
                    symbol=str(symbol),
                    score=raw_score,
                    confidence=confidence,
                    direction=direction,
                    forecast=forecast,
                    asset_name=self._first_non_empty(item.get("asset_name"), item.get("name")),
                    asset_class=self._first_non_empty(item.get("asset_class"), item.get("category")),
                    metadata=item,
                )
            )

        results.sort(key=lambda x: (x.score, x.confidence), reverse=True)
        return results

    def _filter_eligible_signals(self, signals: List[PortfolioSignal]) -> List[PortfolioSignal]:
        filtered: List[PortfolioSignal] = []

        for signal in signals:
            if signal.direction not in {"long", "buy", "overweight"}:
                continue
            if signal.score <= self.min_score_threshold:
                continue
            if signal.confidence <= 0.0:
                continue
            filtered.append(signal)

        filtered.sort(key=lambda x: self._signal_strength(x), reverse=True)
        return filtered

    # -----------------------------
    # Weighting
    # -----------------------------

    def _compute_target_weights(
        self,
        signals: List[PortfolioSignal],
    ) -> Tuple[Dict[str, float], float]:
        strengths = {signal.symbol: self._signal_strength(signal) for signal in signals}
        total_strength = sum(strengths.values())

        if total_strength <= 0:
            return {}, 1.0

        avg_confidence = sum(s.confidence for s in signals) / max(len(signals), 1)
        reserve_cash = self._dynamic_cash_reserve(avg_confidence=avg_confidence, signal_count=len(signals))
        investable_weight = round(1.0 - reserve_cash, 6)

        raw_weights = {
            symbol: (strength / total_strength) * investable_weight
            for symbol, strength in strengths.items()
        }

        adjusted_weights = self._apply_weight_constraints(raw_weights)
        return adjusted_weights, reserve_cash

    def _signal_strength(self, signal: PortfolioSignal) -> float:
        score_component = max(signal.score, 0.0) ** self.score_power
        confidence_component = max(signal.confidence, 0.01) ** self.confidence_power
        return score_component * confidence_component

    def _dynamic_cash_reserve(self, avg_confidence: float, signal_count: int) -> float:
        """
        Weniger Vertrauen oder wenige valide Signale => mehr Cash.
        """
        confidence_penalty = max(0.0, 0.70 - avg_confidence) * 0.35
        concentration_penalty = 0.10 if signal_count <= 2 else 0.05 if signal_count <= 4 else 0.0
        reserve_cash = self.reserve_cash_floor + confidence_penalty + concentration_penalty
        return round(min(max(reserve_cash, self.reserve_cash_floor), self.reserve_cash_ceiling), 6)

    def _apply_weight_constraints(self, raw_weights: Dict[str, float]) -> Dict[str, float]:
        if not raw_weights:
            return {}

        weights = dict(raw_weights)

        # Step 1: Cap large positions
        capped_pool = 0.0
        uncapped_symbols: List[str] = []

        for symbol, weight in list(weights.items()):
            if weight > self.max_position_weight:
                capped_pool += weight - self.max_position_weight
                weights[symbol] = self.max_position_weight
            else:
                uncapped_symbols.append(symbol)

        # Redistribute capped excess
        if capped_pool > 0 and uncapped_symbols:
            uncapped_total = sum(weights[s] for s in uncapped_symbols)
            if uncapped_total > 0:
                for symbol in uncapped_symbols:
                    weights[symbol] += capped_pool * (weights[symbol] / uncapped_total)

        # Step 2: Enforce minimum weights where possible
        underweight_symbols = [s for s, w in weights.items() if w < self.min_position_weight]
        if underweight_symbols and len(weights) * self.min_position_weight <= sum(weights.values()):
            needed = 0.0
            for symbol in underweight_symbols:
                needed += self.min_position_weight - weights[symbol]
                weights[symbol] = self.min_position_weight

            overweight_symbols = [s for s, w in weights.items() if w > self.min_position_weight]
            overweight_total_excess = sum(weights[s] - self.min_position_weight for s in overweight_symbols)

            if needed > 0 and overweight_total_excess > 0:
                for symbol in overweight_symbols:
                    removable = weights[symbol] - self.min_position_weight
                    deduction = needed * (removable / overweight_total_excess)
                    weights[symbol] -= deduction

        # Step 3: Normalize back to <= 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v / total * total, 6) for k, v in weights.items()}

        # final rounding cleanup
        total = round(sum(weights.values()), 6)
        if total > 1.0:
            factor = 1.0 / total
            weights = {k: round(v * factor, 6) for k, v in weights.items()}

        return weights

    # -----------------------------
    # Rebalancing
    # -----------------------------

    def _build_positions(
        self,
        signals: List[PortfolioSignal],
        target_weights: Dict[str, float],
        current_weights: Dict[str, float],
    ) -> Tuple[List[PortfolioPosition], bool, str]:
        positions: List[PortfolioPosition] = []
        rebalance_required = False
        reasons: List[str] = []

        target_symbols = set(target_weights.keys())
        current_symbols = set(current_weights.keys())

        exited_symbols = current_symbols - target_symbols
        new_symbols = target_symbols - current_symbols

        if exited_symbols:
            rebalance_required = True
            reasons.append("symbol_exit")

        if new_symbols:
            rebalance_required = True
            reasons.append("new_symbol")

        for signal in signals:
            target_weight = round(target_weights.get(signal.symbol, 0.0), 6)
            current_weight = round(current_weights.get(signal.symbol, 0.0), 6)
            delta = round(target_weight - current_weight, 6)

            if current_weight == 0 and target_weight > 0:
                action = "NEW"
            elif target_weight == 0 and current_weight > 0:
                action = "EXIT"
            elif abs(delta) >= self.rebalance_drift_threshold:
                action = "BUY" if delta > 0 else "SELL"
            else:
                action = "HOLD"

            if action in {"NEW", "EXIT", "BUY", "SELL"}:
                rebalance_required = True

            if abs(delta) >= self.rebalance_drift_threshold:
                reasons.append(f"drift:{signal.symbol}")

            positions.append(
                PortfolioPosition(
                    symbol=signal.symbol,
                    target_weight=target_weight,
                    current_weight=current_weight,
                    delta=delta,
                    score=round(signal.score, 6),
                    confidence=round(signal.confidence, 6),
                    direction=signal.direction,
                    forecast=signal.forecast,
                    asset_name=signal.asset_name,
                    asset_class=signal.asset_class,
                    action=action,
                )
            )

        # Add exited positions that are no longer in target portfolio
        for symbol in sorted(exited_symbols):
            current_weight = round(current_weights.get(symbol, 0.0), 6)
            positions.append(
                PortfolioPosition(
                    symbol=symbol,
                    target_weight=0.0,
                    current_weight=current_weight,
                    delta=round(-current_weight, 6),
                    score=0.0,
                    confidence=0.0,
                    direction="exit",
                    forecast=None,
                    asset_name=None,
                    asset_class=None,
                    action="EXIT",
                )
            )

        positions.sort(key=lambda p: (p.target_weight, p.score, p.confidence), reverse=True)

        rebalance_reason = "none"
        if reasons:
            unique_reasons = sorted(set(reasons))
            rebalance_reason = ",".join(unique_reasons)

        return positions, rebalance_required, rebalance_reason

    def _build_allocation_hint(self, positions: List[PortfolioPosition], cash_weight: float) -> str:
        if not positions:
            return "DEFENSIVE_CASH"

        avg_confidence = sum(p.confidence for p in positions if p.target_weight > 0) / max(
            len([p for p in positions if p.target_weight > 0]),
            1,
        )

        max_weight = max((p.target_weight for p in positions), default=0.0)

        if cash_weight >= 0.20:
            return "CAUTIOUS_RISK_ON"
        if avg_confidence >= 0.75 and max_weight <= 0.25:
            return "BALANCED_GROWTH"
        if avg_confidence >= 0.75 and max_weight > 0.25:
            return "HIGH_CONVICTION"
        return "MODERATE_RISK"

    # -----------------------------
    # SQLite Persistence
    # -----------------------------

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_created
                ON portfolio_snapshots(user_id, created_at DESC)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        payload = json.dumps(asdict(snapshot), ensure_ascii=False)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO portfolio_snapshots (user_id, generated_at, snapshot_json)
                VALUES (?, ?, ?)
                """,
                (snapshot.user_id, snapshot.generated_at, payload),
            )
            conn.commit()
        finally:
            conn.close()

    def _load_latest_snapshot(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT snapshot_json
                FROM portfolio_snapshots
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return json.loads(row[0])
        finally:
            conn.close()

    def _extract_current_weights(self, snapshot: Optional[Dict[str, Any]]) -> Dict[str, float]:
        if not snapshot:
            return {}

        positions = snapshot.get("positions", [])
        results: Dict[str, float] = {}

        for position in positions:
            symbol = position.get("symbol")
            weight = self._safe_float(position.get("target_weight"), 0.0)
            if symbol:
                results[str(symbol)] = weight

        return results

    # -----------------------------
    # Helpers
    # -----------------------------

    def _normalize_confidence(self, value: float) -> float:
        """
        Unterstützt 0..1 und 0..100.
        """
        if value is None:
            return 0.5
        if value > 1.0:
            value = value / 100.0
        return round(min(max(value, 0.0), 1.0), 6)

    def _safe_float(self, value: Any, default: Optional[float] = 0.0) -> Optional[float]:
        if value is None:
            return default
        try:
            if isinstance(value, bool):
                return default
            numeric = float(value)
            if math.isnan(numeric) or math.isinf(numeric):
                return default
            return numeric
        except (TypeError, ValueError):
            return default

    def _first_non_empty(self, *values: Any) -> Optional[Any]:
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    def _utcnow_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()