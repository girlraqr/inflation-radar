from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from live.repository.mapping_repository import MappingRepository

from shared.constants.signal_asset_mapping import (
    DEFAULT_REGIME,
    DEFAULT_SIGNAL,
    DEFAULT_UNKNOWN_SIGNAL_THEME,
    REGIME_THEME_TILTS,
    SIGNAL_ALIASES,
    SIGNAL_THEME_MAP,
    THEME_REGISTRY,
)


@dataclass(frozen=True)
class SignalMappingResult:
    canonical_signal: str
    regime: str
    conviction: float
    theme_mix: Dict[str, float]
    asset_weights: Dict[str, float]
    rationale: str


class SignalAssetMappingService:

    def __init__(self):
        self.mapping_repository = MappingRepository()

    # =========================================================
    # PUBLIC
    # =========================================================

    def map_signals_to_assets(
        self,
        signals: Iterable[Any],
        regime: Optional[str] = None,
        top_n: int = 3,
        min_conviction: float = 0.0,
    ) -> Dict[str, Any]:

        normalized_signals = self._normalize_signals(signals)
        normalized_signals = [
            s for s in normalized_signals if s["conviction"] >= min_conviction
        ]

        if not normalized_signals:
            normalized_signals = [{
                "signal": DEFAULT_SIGNAL,
                "conviction": 1.0,
                "score": 1.0,
                "raw": {"signal": DEFAULT_SIGNAL, "conviction": 1.0},
            }]

        normalized_signals = sorted(
            normalized_signals,
            key=lambda x: (x["conviction"], x["score"]),
            reverse=True,
        )[:top_n]

        active_regime = self._normalize_regime(regime)
        aggregate_weights: Dict[str, float] = {}
        mapping_breakdown: List[Dict[str, Any]] = []

        total_signal_strength = sum(max(s["conviction"], 0.0) for s in normalized_signals) or 1.0

        for signal_row in normalized_signals:
            conviction = max(signal_row["conviction"], 0.0)
            signal_strength = conviction / total_signal_strength

            mapped = self.map_single_signal(
                signal=signal_row["signal"],
                conviction=conviction,
                regime=active_regime,
            )

            for asset, weight in mapped.asset_weights.items():
                aggregate_weights[asset] = aggregate_weights.get(asset, 0.0) + (weight * signal_strength)

            mapping_breakdown.append({
                "input_signal": signal_row["raw"],
                "canonical_signal": mapped.canonical_signal,
                "regime": mapped.regime,
                "conviction": round(mapped.conviction, 6),
                "theme_mix": self._round_dict(mapped.theme_mix),
                "asset_weights": self._round_dict(mapped.asset_weights),
                "rationale": mapped.rationale,
            })

        final_weights = self._normalize_weights(aggregate_weights)

        return {
            "regime": active_regime,
            "weights": self._round_dict(final_weights),
            "mapping_breakdown": mapping_breakdown,
        }

    # =========================================================
    # CORE MAPPING (FIXED)
    # =========================================================

    def map_single_signal(
        self,
        signal: str,
        conviction: float,
        regime: Optional[str] = None,
    ) -> SignalMappingResult:

        canonical_signal = self._canonicalize_signal(signal)
        active_regime = self._normalize_regime(regime)
        conviction = self._clamp(conviction, 0.0, 1.0)

        # 🔥 DB FIRST
        db_mapping = self._get_mapping_from_db(canonical_signal, active_regime)

        if db_mapping:
            raw_theme_mix, asset_weights = db_mapping

            asset_weights = self._normalize_weights(asset_weights)

            return SignalMappingResult(
                canonical_signal=canonical_signal,
                regime=active_regime,
                conviction=conviction,
                theme_mix=self._round_dict(raw_theme_mix),
                asset_weights=self._round_dict(asset_weights),
                rationale="DB-driven mapping",
            )

        # 🔁 FALLBACK
        raw_theme_mix = dict(self._get_theme_mix_for_signal(canonical_signal))
        tilted_theme_mix = self._apply_regime_tilts(raw_theme_mix, active_regime)
        normalized_theme_mix = self._normalize_weights(tilted_theme_mix)

        asset_weights: Dict[str, float] = {}
        for theme_name, theme_weight in normalized_theme_mix.items():
            theme = THEME_REGISTRY[theme_name]
            for asset, asset_weight in theme.assets.items():
                asset_weights[asset] = asset_weights.get(asset, 0.0) + (
                    theme_weight * asset_weight
                )

        asset_weights = self._normalize_weights(asset_weights)

        rationale = self._build_rationale(
            canonical_signal=canonical_signal,
            regime=active_regime,
            conviction=conviction,
            theme_mix=normalized_theme_mix,
        )

        return SignalMappingResult(
            canonical_signal=canonical_signal,
            regime=active_regime,
            conviction=conviction,
            theme_mix=self._round_dict(normalized_theme_mix),
            asset_weights=self._round_dict(asset_weights),
            rationale=rationale,
        )

    # =========================================================
    # 🔥 FIXED DB LOGIC
    # =========================================================

    def _get_mapping_from_db(self, signal: str, regime: str):

        rows = self.mapping_repository.get_mapping(signal, regime)

        if not rows:
            return None

        theme_mix: Dict[str, float] = {}
        asset_weights: Dict[str, float] = {}

        for r in rows:
            theme = r["theme"]
            theme_weight = float(r["theme_weight"])
            asset = r["asset"]
            asset_weight = float(r["asset_weight"])

            # 🔥 FIX: theme_weight NICHT aufsummieren!
            if theme not in theme_mix:
                theme_mix[theme] = theme_weight

            # Asset aggregation bleibt korrekt
            asset_weights[asset] = asset_weights.get(asset, 0.0) + (
                theme_weight * asset_weight
            )

        return theme_mix, asset_weights

    # =========================================================
    # HELPERS
    # =========================================================

    def _normalize_signals(self, signals: Iterable[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for item in signals or []:
            signal_name = None
            conviction = None
            score = None

            if isinstance(item, Mapping):
                signal_name = (
                    item.get("signal")
                    or item.get("name")
                    or item.get("label")
                    or item.get("regime")
                )
                conviction = item.get("conviction", item.get("strength", item.get("weight", 0.0)))
                score = item.get("score", conviction)
            else:
                signal_name = getattr(item, "signal", None) or getattr(item, "name", None)
                conviction = getattr(item, "conviction", None)
                if conviction is None:
                    conviction = getattr(item, "strength", None)
                if conviction is None:
                    conviction = getattr(item, "weight", 0.0)
                score = getattr(item, "score", conviction)

            if not signal_name:
                continue

            conviction = 0.0 if conviction is None else float(conviction)
            score = conviction if score is None else float(score)

            normalized.append({
                "signal": str(signal_name),
                "conviction": self._clamp(conviction, 0.0, 1.0),
                "score": score,
                "raw": item,
            })

        return normalized

    def _canonicalize_signal(self, signal: Optional[str]) -> str:
        if not signal:
            return DEFAULT_SIGNAL
        clean = str(signal).strip().lower().replace(" ", "_")
        return SIGNAL_ALIASES.get(clean, clean if clean in SIGNAL_THEME_MAP else DEFAULT_SIGNAL)

    def _normalize_regime(self, regime: Optional[str]) -> str:
        if not regime:
            return DEFAULT_REGIME
        clean = str(regime).strip().lower().replace(" ", "_")
        return clean if clean in REGIME_THEME_TILTS else DEFAULT_REGIME

    def _get_theme_mix_for_signal(self, canonical_signal: str) -> Dict[str, float]:
        if canonical_signal in SIGNAL_THEME_MAP:
            return {theme: weight for theme, weight in SIGNAL_THEME_MAP[canonical_signal]}
        return {DEFAULT_UNKNOWN_SIGNAL_THEME: 1.0}

    def _apply_regime_tilts(self, theme_mix: Dict[str, float], regime: str) -> Dict[str, float]:
        regime_tilts = REGIME_THEME_TILTS.get(regime, {})
        return {
            theme: weight * regime_tilts.get(theme, 1.0)
            for theme, weight in theme_mix.items()
        }

    def _build_rationale(
        self,
        canonical_signal: str,
        regime: str,
        conviction: float,
        theme_mix: Dict[str, float],
    ) -> str:
        ordered = sorted(theme_mix.items(), key=lambda x: x[1], reverse=True)
        top = ", ".join(f"{k}:{v:.2f}" for k, v in ordered[:3])
        return f"Signal '{canonical_signal}' mapped under regime '{regime}' with conviction {conviction:.2f}; theme mix => {top}."

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        positive = {k: max(float(v), 0.0) for k, v in weights.items()}
        total = sum(positive.values())
        if total <= 0:
            return {}
        return {k: v / total for k, v in positive.items()}

    def _round_dict(self, data: Dict[str, float], digits: int = 6) -> Dict[str, float]:
        return {k: round(float(v), digits) for k, v in data.items()}

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, float(value)))