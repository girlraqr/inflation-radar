from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.signal_asset_mapping_service import SignalAssetMappingService

DEFAULT_DB_PATH = "storage/app.db"

# Assets, die direkt investierbar sind und NICHT mehr durch den Mapping-Layer
# geschickt werden sollten.
DIRECT_ALLOCATABLE_ASSETS = {
    "SPY",
    "QQQ",
    "IEF",
    "TLT",
    "SHY",
    "GLD",
    "DBC",
    "TIP",
    "XLE",
    "XLF",
    "UUP",
    "CASH",
}


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
                    "engine_version": "2.1.0",
                    "eligible_signal_count": 0,
                    "raw_signal_count": len(ranked_signals),
                    "allocation_mode": "empty",
                },
            )
            if persist_snapshot:
                self._save_snapshot(snapshot)
            return asdict(snapshot)

        selected_signals = eligible_signals[: self.max_positions]

        # ---------------------------------------------------
        # IMPORTANT:
        # Wenn die Signale bereits investierbare Assets sind
        # (z. B. SPY, DBC, XLE), dann NICHT nochmal durchs
        # Signal→Asset-Mapping schicken.
        # ---------------------------------------------------

        use_direct_assets = self._signals_are_direct_assets(selected_signals)

        mapping_result: Dict[str, Any]
        portfolio_inputs: List[PortfolioSignal]

        if use_direct_assets:
            portfolio_inputs = selected_signals
            mapping_result = {
                "regime": regime,
                "weights": {},
                "mapping_breakdown": [],
                "mode": "direct_asset_signals",
            }
        else:
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

            portfolio_inputs = []
            for symbol, weight in mapped_weights.items():
                portfolio_inputs.append(
                    PortfolioSignal(
                        symbol=symbol,
                        score=float(weight),
                        confidence=1.0,
                        direction="long",
                        forecast=None,
                        asset_name=symbol,
                        asset_class="mapped",
                        metadata={"source": "mapping_layer"},
                    )
                )

        target_weights, reserve_cash = self._compute_target_weights(portfolio_inputs)

        previous_snapshot = self._load_latest_snapshot(user_id=user_id)
        current_weights = self._extract_current_weights(previous_snapshot)

        positions, rebalance_required, rebalance_reason = self._build_positions(
            signals=portfolio_inputs,
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
                "engine_version": "2.1.0",
                "regime": mapping_result.get("regime"),
                "mapping_breakdown": mapping_result.get("mapping_breakdown", []),
                "eligible_signal_count": len(eligible_signals),
                "selected_signal_count": len(selected_signals),
                "raw_signal_count": len(ranked_signals),
                "max_positions": self.max_positions,
                "allocation_mode": (
                    "direct_asset_signals" if use_direct_assets else "mapped_signals"
                ),
                "input_symbols": [s.symbol for s in selected_signals],
            },
        )

        if persist_snapshot:
            self._save_snapshot(snapshot)

        return asdict(snapshot)

    # ---------------------------------------------------
    # ALLOCATION HINT
    # ---------------------------------------------------

    def _build_allocation_hint(
        self,
        positions: List[PortfolioPosition],
        cash_weight: float,
    ) -> str:
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
    # SIGNAL PREP
    # ---------------------------------------------------

    def _normalize_signals(self, ranked_signals: List[Dict[str, Any]]) -> List[PortfolioSignal]:
        results: List[PortfolioSignal] = []

        for item in ranked_signals or []:
            symbol = item.get("symbol") or item.get("name")
            if not symbol:
                continue

            results.append(
                PortfolioSignal(
                    symbol=str(symbol).upper().strip(),
                    score=float(item.get("score", 0.0) or 0.0),
                    confidence=float(item.get("confidence", 0.5) or 0.5),
                    direction=str(item.get("direction", "long")),
                    forecast=item.get("forecast"),
                    asset_name=item.get("asset_name"),
                    asset_class=item.get("asset_class"),
                    metadata=item.get("metadata"),
                )
            )

        return results

    def _filter_eligible_signals(self, signals: List[PortfolioSignal]) -> List[PortfolioSignal]:
        filtered = [
            s
            for s in signals
            if s.score > self.min_score_threshold and s.confidence > 0
        ]
        filtered.sort(key=lambda s: (s.score, s.confidence), reverse=True)
        return filtered

    def _signals_are_direct_assets(self, signals: List[PortfolioSignal]) -> bool:
        if not signals:
            return False
        return all(s.symbol in DIRECT_ALLOCATABLE_ASSETS for s in signals)

    # ---------------------------------------------------
    # WEIGHTS
    # ---------------------------------------------------

    def _compute_target_weights(
        self,
        signals: List[PortfolioSignal],
    ) -> Tuple[Dict[str, float], float]:
        if not signals:
            return {}, 1.0

        strengths: Dict[str, float] = {}

        for s in signals:
            score_component = max(float(s.score), 0.0) ** self.score_power
            confidence_component = max(float(s.confidence), 0.0) ** self.confidence_power
            strength = score_component * confidence_component
            strengths[s.symbol] = strengths.get(s.symbol, 0.0) + strength

        total_strength = sum(strengths.values())

        if total_strength <= 0:
            return {}, 1.0

        raw_weights = {symbol: val / total_strength for symbol, val in strengths.items()}

        bounded = self._apply_weight_bounds(raw_weights)

        invested_weight = sum(bounded.values())
        reserve_cash = max(0.0, 1.0 - invested_weight)

        reserve_cash = min(
            max(reserve_cash, self.reserve_cash_floor),
            self.reserve_cash_ceiling,
        )

        capital_to_allocate = max(0.0, 1.0 - reserve_cash)

        if capital_to_allocate <= 0:
            return {}, 1.0

        scaled = self._scale_weights_to_total(bounded, capital_to_allocate)

        return scaled, reserve_cash

    def _apply_weight_bounds(self, weights: Dict[str, float]) -> Dict[str, float]:
        if not weights:
            return {}

        bounded = {k: max(self.min_position_weight, min(v, self.max_position_weight)) for k, v in weights.items()}
        total = sum(bounded.values())

        if total <= 0:
            return {}

        return {k: v / total for k, v in bounded.items()}

    def _scale_weights_to_total(
        self,
        weights: Dict[str, float],
        target_total: float,
    ) -> Dict[str, float]:
        total = sum(weights.values())
        if total <= 0:
            return {}

        scaled = {k: (v / total) * target_total for k, v in weights.items()}
        return {k: round(v, 6) for k, v in scaled.items()}

    # ---------------------------------------------------
    # POSITIONS
    # ---------------------------------------------------

    def _build_positions(
        self,
        signals: List[PortfolioSignal],
        target_weights: Dict[str, float],
        current_weights: Dict[str, float],
    ) -> Tuple[List[PortfolioPosition], bool, str]:
        positions: List[PortfolioPosition] = []

        all_symbols = set(target_weights.keys()) | set(current_weights.keys())
        signal_lookup = {s.symbol: s for s in signals}

        rebalance_required = False
        rebalance_reasons: List[str] = []

        for symbol in sorted(all_symbols):
            target_weight = float(target_weights.get(symbol, 0.0))
            current_weight = float(current_weights.get(symbol, 0.0))
            delta = round(target_weight - current_weight, 6)

            signal = signal_lookup.get(
                symbol,
                PortfolioSignal(
                    symbol=symbol,
                    score=0.0,
                    confidence=0.0,
                    direction="long",
                    forecast=None,
                    asset_name=symbol,
                    asset_class=None,
                    metadata=None,
                ),
            )

            action = self._derive_action(
                target_weight=target_weight,
                current_weight=current_weight,
                delta=delta,
            )

            if abs(delta) >= self.rebalance_drift_threshold:
                rebalance_required = True
                rebalance_reasons.append(f"{symbol}:{delta:+.2%}")

            positions.append(
                PortfolioPosition(
                    symbol=symbol,
                    target_weight=round(target_weight, 6),
                    current_weight=round(current_weight, 6),
                    delta=delta,
                    score=round(float(signal.score), 6),
                    confidence=round(float(signal.confidence), 6),
                    direction=signal.direction,
                    forecast=signal.forecast,
                    asset_name=signal.asset_name or symbol,
                    asset_class=signal.asset_class,
                    action=action,
                )
            )

        positions = [p for p in positions if p.target_weight > 0 or p.current_weight > 0]

        reason = "none"
        if rebalance_required:
            reason = "; ".join(rebalance_reasons[:10])

        return positions, rebalance_required, reason

    def _derive_action(
        self,
        target_weight: float,
        current_weight: float,
        delta: float,
    ) -> str:
        if current_weight <= 0 and target_weight > 0:
            return "BUY"

        if current_weight > 0 and target_weight <= 0:
            return "SELL"

        if delta > self.rebalance_drift_threshold:
            return "INCREASE"

        if delta < -self.rebalance_drift_threshold:
            return "DECREASE"

        return "HOLD"

    # ---------------------------------------------------
    # DB
    # ---------------------------------------------------

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                generated_at TEXT,
                snapshot_json TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO portfolio_snapshots (user_id, generated_at, snapshot_json)
            VALUES (?, ?, ?)
            """,
            (snapshot.user_id, snapshot.generated_at, json.dumps(asdict(snapshot))),
        )
        conn.commit()
        conn.close()

    def _load_latest_snapshot(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT snapshot_json
            FROM portfolio_snapshots
            WHERE user_id = ?
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            (user_id,),
        )

        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        try:
            return json.loads(row[0])
        except Exception:
            return None

    def _extract_current_weights(self, snapshot: Optional[Dict[str, Any]]) -> Dict[str, float]:
        if not snapshot:
            return {}

        positions = snapshot.get("positions", [])
        weights: Dict[str, float] = {}

        for p in positions:
            symbol = p.get("symbol")
            target_weight = p.get("target_weight")
            if not symbol:
                continue
            try:
                weights[str(symbol).upper()] = float(target_weight or 0.0)
            except (TypeError, ValueError):
                continue

        return weights

    def _utcnow_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()