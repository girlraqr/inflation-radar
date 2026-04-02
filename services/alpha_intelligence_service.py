from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd


class AlphaIntelligenceService:
    # ---------------------------------------------------
    # PUBLIC
    # ---------------------------------------------------

    def build_alpha_intelligence(
        self,
        base_history: pd.DataFrame,
        risk_history: pd.DataFrame,
        snapshots_df: pd.DataFrame,
    ) -> Dict[str, Any]:

        if base_history.empty or risk_history.empty:
            return self._empty()

        merged = self._align_histories(base_history, risk_history)

        if merged.empty:
            return self._empty()

        rolling_alpha = self._build_rolling_alpha(merged)
        regime_alpha = self._build_regime_alpha(merged, snapshots_df)
        narratives = self._build_alpha_narratives(rolling_alpha, regime_alpha)

        return {
            "rolling_alpha": rolling_alpha,
            "regime_alpha": regime_alpha,
            "alpha_narratives": narratives,
        }

    # ---------------------------------------------------
    # EMPTY
    # ---------------------------------------------------

    def _empty(self) -> Dict[str, Any]:
        return {
            "rolling_alpha": [],
            "regime_alpha": {},
            "alpha_narratives": [],
        }

    # ---------------------------------------------------
    # ALIGNMENT
    # ---------------------------------------------------

    def _align_histories(
        self,
        base: pd.DataFrame,
        risk: pd.DataFrame,
    ) -> pd.DataFrame:

        base_df = base.copy()
        risk_df = risk.copy()

        base_df["date"] = pd.to_datetime(base_df["date"], errors="coerce")
        risk_df["date"] = pd.to_datetime(risk_df["date"], errors="coerce")

        base_df = base_df.dropna(subset=["date"])
        risk_df = risk_df.dropna(subset=["date"])

        base_df = base_df.rename(
            columns={
                "period_return": "base_return",
                "portfolio_value": "base_value",
            }
        )

        risk_df = risk_df.rename(
            columns={
                "period_return": "risk_return",
                "portfolio_value": "risk_value",
            }
        )

        merged = pd.merge(
            base_df,
            risk_df,
            on="date",
            how="inner",
        )

        merged = merged.drop_duplicates(subset=["date"])
        merged = merged.sort_values("date").reset_index(drop=True)

        return merged

    # ---------------------------------------------------
    # ROLLING ALPHA
    # ---------------------------------------------------

    def _build_rolling_alpha(
        self,
        df: pd.DataFrame,
    ) -> List[Dict[str, Any]]:

        if df.empty:
            return []

        df = df.copy().sort_values("date").reset_index(drop=True)

        # Fallback bei sehr wenig Daten
        if len(df) < 2:
            row = df.iloc[0]
            base_r = float(row["base_return"])
            risk_r = float(row["risk_return"])
            delta = risk_r - base_r

            return [
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "return_delta": float(delta),
                    "volatility_reduction": 0.0,
                    "drawdown_reduction": 0.0,
                    "efficiency_score": float(delta),
                }
            ]

        window = min(3, len(df))
        results: List[Dict[str, Any]] = []

        for i in range(window - 1, len(df)):
            window_df = df.iloc[i - window + 1 : i + 1]

            base_returns = window_df["base_return"].astype(float)
            risk_returns = window_df["risk_return"].astype(float)

            base_total = float((1.0 + base_returns).prod() - 1.0)
            risk_total = float((1.0 + risk_returns).prod() - 1.0)
            return_delta = risk_total - base_total

            base_vol = float(base_returns.std()) if len(base_returns) > 1 else 0.0
            risk_vol = float(risk_returns.std()) if len(risk_returns) > 1 else 0.0

            volatility_reduction = (
                (base_vol - risk_vol) / base_vol if base_vol != 0 else 0.0
            )

            base_dd = self._max_drawdown_from_returns(base_returns)
            risk_dd = self._max_drawdown_from_returns(risk_returns)

            drawdown_reduction = (
                (base_dd - risk_dd) / abs(base_dd) if base_dd != 0 else 0.0
            )

            denom = abs(volatility_reduction) + abs(drawdown_reduction)
            efficiency_score = return_delta / denom if denom != 0 else return_delta

            results.append(
                {
                    "date": window_df["date"].iloc[-1].strftime("%Y-%m-%d"),
                    "return_delta": float(return_delta),
                    "volatility_reduction": float(volatility_reduction),
                    "drawdown_reduction": float(drawdown_reduction),
                    "efficiency_score": float(efficiency_score),
                }
            )

        return results

    # ---------------------------------------------------
    # REGIME ALPHA
    # ---------------------------------------------------

    def _build_regime_alpha(
        self,
        merged: pd.DataFrame,
        snapshots_df: pd.DataFrame,
    ) -> Dict[str, Any]:

        if snapshots_df.empty:
            return {}

        snapshots = snapshots_df.copy()

        if "snapshot_date" not in snapshots.columns:
            if "generated_at" in snapshots.columns:
                snapshots["snapshot_date"] = snapshots["generated_at"]
            else:
                return {}

        snapshots["snapshot_date"] = pd.to_datetime(
            snapshots["snapshot_date"], errors="coerce"
        )
        snapshots = snapshots.dropna(subset=["snapshot_date"])
        snapshots = snapshots.sort_values("snapshot_date")
        snapshots = snapshots.drop_duplicates(subset=["snapshot_date"], keep="last")

        regime_context = snapshots[["snapshot_date", "meta"]].copy()

        df = pd.merge(
            merged.copy(),
            regime_context,
            left_on="date",
            right_on="snapshot_date",
            how="left",
        )

        if df.empty:
            return {}

        df["regime"] = df["meta"].apply(self._derive_regime_label)
        df["base_return"] = df["base_return"].astype(float)
        df["risk_return"] = df["risk_return"].astype(float)
        df["return_delta"] = df["risk_return"] - df["base_return"]

        grouped: Dict[str, Any] = {}

        for regime, group in df.groupby("regime"):
            if group.empty:
                continue

            base_returns = group["base_return"]
            risk_returns = group["risk_return"]

            base_total = float((1.0 + base_returns).prod() - 1.0)
            risk_total = float((1.0 + risk_returns).prod() - 1.0)
            return_delta = risk_total - base_total

            base_vol = float(base_returns.std()) if len(base_returns) > 1 else 0.0
            risk_vol = float(risk_returns.std()) if len(risk_returns) > 1 else 0.0
            volatility_reduction = (
                (base_vol - risk_vol) / base_vol if base_vol != 0 else 0.0
            )

            base_dd = self._max_drawdown_from_returns(base_returns)
            risk_dd = self._max_drawdown_from_returns(risk_returns)
            drawdown_reduction = (
                (base_dd - risk_dd) / abs(base_dd) if base_dd != 0 else 0.0
            )

            denom = abs(volatility_reduction) + abs(drawdown_reduction)
            efficiency_score = return_delta / denom if denom != 0 else return_delta

            grouped[str(regime)] = {
                "observations": int(len(group)),
                "return_delta": float(return_delta),
                "volatility_reduction": float(volatility_reduction),
                "drawdown_reduction": float(drawdown_reduction),
                "efficiency_score": float(efficiency_score),
                "avg_period_alpha": float(group["return_delta"].mean()),
            }

        return grouped

    # ---------------------------------------------------
    # REGIME DERIVATION
    # ---------------------------------------------------

    def _derive_regime_label(self, meta: Any) -> str:
        payload = self._safe_parse_meta(meta)

        if not isinstance(payload, dict):
            return "neutral"

        explicit_regime = payload.get("regime")
        if isinstance(explicit_regime, str) and explicit_regime.strip():
            return explicit_regime.strip().lower()

        risk_state = payload.get("risk_state")
        if isinstance(risk_state, str) and risk_state.strip():
            return risk_state.strip().lower()

        overlay = payload.get("risk_overlay")
        if isinstance(overlay, dict):
            overlay_state = overlay.get("state")
            if isinstance(overlay_state, str) and overlay_state.strip():
                return overlay_state.strip().lower()

            if overlay.get("risk_off") is True:
                return "risk_off"

            if overlay.get("active") is True:
                return "risk_managed"

        risk_score = self._safe_float(payload.get("risk_score"))
        confidence = self._safe_float(payload.get("confidence"))

        if risk_score is not None:
            if risk_score >= 0.75:
                return "risk_off"
            if risk_score >= 0.40:
                return "elevated_risk"
            return "risk_on"

        if confidence is not None:
            if confidence >= 0.75:
                return "high_confidence"
            if confidence >= 0.50:
                return "medium_confidence"
            return "low_confidence"

        return "neutral"

    # ---------------------------------------------------
    # META HELPERS
    # ---------------------------------------------------

    def _safe_parse_meta(self, meta: Any) -> Any:
        if isinstance(meta, dict):
            return meta

        if isinstance(meta, str):
            meta = meta.strip()
            if not meta:
                return {}
            try:
                return json.loads(meta)
            except Exception:
                return {}

        return {}

    def _safe_float(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    # ---------------------------------------------------
    # DRAWDOWN HELPER
    # ---------------------------------------------------

    def _max_drawdown_from_returns(self, returns: pd.Series) -> float:
        if returns.empty:
            return 0.0

        cumulative = (1.0 + returns.astype(float)).cumprod()
        rolling_peak = cumulative.cummax()
        drawdown = cumulative / rolling_peak - 1.0
        return float(drawdown.min())

    # ---------------------------------------------------
    # NARRATIVES
    # ---------------------------------------------------

    def _build_alpha_narratives(
        self,
        rolling_alpha: List[Dict[str, Any]],
        regime_alpha: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        narratives: List[Dict[str, Any]] = []

        if not rolling_alpha:
            return narratives

        avg_alpha = sum(item["return_delta"] for item in rolling_alpha) / len(rolling_alpha)

        if avg_alpha < 0:
            narratives.append(
                {
                    "title": "Risk Overlay reduziert Performance",
                    "status": "warning",
                    "message": "Das Risk Overlay liefert aktuell negatives Alpha gegenüber dem Base Portfolio.",
                }
            )
        else:
            narratives.append(
                {
                    "title": "Risk Overlay erzeugt Alpha",
                    "status": "positive",
                    "message": "Das Risk Overlay verbessert aktuell die Performance gegenüber dem Base Portfolio.",
                }
            )

        if regime_alpha:
            best_regime, best_stats = max(
                regime_alpha.items(),
                key=lambda item: item[1].get("return_delta", 0.0),
            )

            worst_regime, worst_stats = min(
                regime_alpha.items(),
                key=lambda item: item[1].get("return_delta", 0.0),
            )

            narratives.append(
                {
                    "title": "Stärkstes Regime",
                    "status": "info",
                    "message": (
                        f"Das stärkste Alpha entsteht aktuell im Regime "
                        f"'{best_regime}' mit einem Return-Delta von "
                        f"{best_stats.get('return_delta', 0.0):.4f}."
                    ),
                }
            )

            if best_regime != worst_regime:
                narratives.append(
                    {
                        "title": "Schwächstes Regime",
                        "status": "warning",
                        "message": (
                            f"Das schwächste Alpha entsteht aktuell im Regime "
                            f"'{worst_regime}' mit einem Return-Delta von "
                            f"{worst_stats.get('return_delta', 0.0):.4f}."
                        ),
                    }
                )

        return narratives