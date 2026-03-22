from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from live.repository.live_signal_repository import LiveSignalRepository


@dataclass
class LiveSignalConfig:
    predictions_path: str = "storage/cache/predictions.csv"
    signal_history_path: str = "storage/cache/signal_history.csv"
    top_n: int = 3
    min_weight: float = 0.0


class LiveSignalService:
    def __init__(
        self,
        repository: LiveSignalRepository | None = None,
        config: LiveSignalConfig | None = None,
    ) -> None:
        self.repository = repository or LiveSignalRepository()
        self.config = config or LiveSignalConfig()

    def build_and_publish_live_signal(self) -> Dict[str, Any]:
        self._set_status("running", "Live-Signal-Berechnung gestartet.")

        try:
            predictions_df = self._load_predictions()
            latest_row = self._get_latest_prediction_row(predictions_df)

            regime = self._infer_regime(latest_row)
            ranking = self._build_ranking(latest_row)
            allocation = self._build_allocation(ranking)
            confidence = self._extract_confidence(latest_row)
            signal_strength = self._extract_signal_strength(latest_row)
            regime_score = self._extract_regime_score(latest_row)
            as_of_date = self._extract_as_of_date(latest_row)
            rebalance_flag = self._compute_rebalance_flag(allocation)

            payload = {
                "as_of_date": as_of_date,
                "published_at": datetime.utcnow().isoformat(),
                "regime": regime,
                "regime_score": regime_score,
                "signal_strength": signal_strength,
                "confidence": confidence,
                "rebalance_flag": rebalance_flag,
                "top_n": self.config.top_n,
                "ranking": ranking,
                "allocation": allocation,
                "meta": {
                    "source": "live_signal_service",
                    "ranking_version": "C",
                    "allocation_mode": "top_n_equal_weight",
                },
            }

            self.repository.save_current_signal(payload)
            self.repository.save_current_regime(
                {
                    "as_of_date": as_of_date,
                    "published_at": payload["published_at"],
                    "regime": regime,
                    "regime_score": regime_score,
                    "confidence": confidence,
                }
            )
            self.repository.save_current_allocation(
                {
                    "as_of_date": as_of_date,
                    "published_at": payload["published_at"],
                    "rebalance_flag": rebalance_flag,
                    "allocation": allocation,
                }
            )
            self.repository.append_history_item(
                {
                    "as_of_date": as_of_date,
                    "regime": regime,
                    "confidence": confidence,
                    "signal_strength": signal_strength,
                    "rebalance_flag": rebalance_flag,
                }
            )

            self._set_status("ok", "Live-Signal erfolgreich veröffentlicht.")
            return payload

        except Exception as exc:
            self._set_status("error", f"Fehler bei Live-Signal-Berechnung: {exc}")
            raise

    def get_current_signal(self) -> Dict[str, Any]:
        return self.repository.load_current_signal()

    def get_current_allocation(self) -> Dict[str, Any]:
        return self.repository.load_current_allocation()

    def get_current_regime(self) -> Dict[str, Any]:
        return self.repository.load_current_regime()

    def get_status(self) -> Dict[str, Any]:
        return self.repository.load_live_status()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.repository.load_history(limit=limit)

    def _load_predictions(self) -> pd.DataFrame:
        path = Path(self.config.predictions_path)
        if not path.exists():
            raise FileNotFoundError(f"Predictions-Datei nicht gefunden: {path}")

        df = pd.read_csv(path)
        if df.empty:
            raise ValueError("Predictions-Datei ist leer.")

        return df

    def _get_latest_prediction_row(self, df: pd.DataFrame) -> pd.Series:
        date_col = self._resolve_date_column(df)
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])

        if df.empty:
            raise ValueError("Keine gültigen Datumswerte in predictions.csv gefunden.")

        df = df.sort_values(date_col)
        return df.iloc[-1]

    def _resolve_date_column(self, df: pd.DataFrame) -> str:
        candidates = ["date", "as_of_date", "timestamp", "Date"]
        for col in candidates:
            if col in df.columns:
                return col
        raise ValueError(
            f"Keine Datums-Spalte gefunden. Erwartet eine von: {candidates}"
        )

    def _infer_regime(self, row: pd.Series) -> str:
        if "predicted_regime" in row.index:
            return str(row["predicted_regime"])

        prob_cols = [col for col in row.index if str(col).startswith("proba_")]
        if prob_cols:
            best_col = max(prob_cols, key=lambda col: float(row[col]))
            return best_col.replace("proba_", "").upper()

        inflation = self._safe_float(row.get("inflation_signal", 0.0))
        growth = self._safe_float(row.get("growth_signal", 0.0))

        if inflation >= 0 and growth >= 0:
            return "REFLATION"
        if inflation >= 0 and growth < 0:
            return "STAGFLATION"
        if inflation < 0 and growth >= 0:
            return "GOLDILOCKS"
        return "DEFLATION"

    def _build_ranking(self, row: pd.Series) -> List[str]:
        rank_cols = [col for col in row.index if str(col).startswith("rank_")]
        if rank_cols:
            sorted_cols = sorted(
                rank_cols,
                key=lambda col: self._safe_float(row[col]),
                reverse=True,
            )
            ranking = [col.replace("rank_", "").upper() for col in sorted_cols]
            return ranking[: self.config.top_n]

        score_cols = [col for col in row.index if str(col).startswith("score_")]
        if score_cols:
            sorted_cols = sorted(
                score_cols,
                key=lambda col: self._safe_float(row[col]),
                reverse=True,
            )
            ranking = [col.replace("score_", "").upper() for col in sorted_cols]
            return ranking[: self.config.top_n]

        fallback = ["TIP", "GLD", "IEF", "DBC", "SPY"]
        return fallback[: self.config.top_n]

    def _build_allocation(self, ranking: List[str]) -> List[Dict[str, float]]:
        if not ranking:
            raise ValueError("Ranking leer. Allocation kann nicht berechnet werden.")

        weight = round(1.0 / len(ranking), 4)
        return [{"asset": asset, "weight": weight} for asset in ranking]

    def _extract_confidence(self, row: pd.Series) -> float:
        for key in ["confidence", "signal_confidence", "max_probability"]:
            if key in row.index:
                return round(self._safe_float(row[key]), 4)

        prob_cols = [col for col in row.index if str(col).startswith("proba_")]
        if prob_cols:
            return round(max(self._safe_float(row[col]) for col in prob_cols), 4)

        return 0.0

    def _extract_signal_strength(self, row: pd.Series) -> float:
        for key in ["signal_strength", "conviction", "momentum_score"]:
            if key in row.index:
                return round(self._safe_float(row[key]), 4)
        return 0.0

    def _extract_regime_score(self, row: pd.Series) -> float:
        for key in ["regime_score", "regime_strength", "macro_score"]:
            if key in row.index:
                return round(self._safe_float(row[key]), 4)
        return 0.0

    def _extract_as_of_date(self, row: pd.Series) -> str:
        for key in ["date", "as_of_date", "timestamp", "Date"]:
            if key in row.index:
                parsed = pd.to_datetime(row[key], errors="coerce")
                if pd.notna(parsed):
                    return parsed.date().isoformat()

        return datetime.utcnow().date().isoformat()

    def _compute_rebalance_flag(self, allocation: List[Dict[str, float]]) -> bool:
        current_payload = self.repository.load_current_allocation()
        current_allocation = current_payload.get("allocation", [])

        if not current_allocation:
            return True

        old_map = {item["asset"]: float(item["weight"]) for item in current_allocation}
        new_map = {item["asset"]: float(item["weight"]) for item in allocation}

        if set(old_map.keys()) != set(new_map.keys()):
            return True

        threshold = 0.05
        for asset in new_map:
            if abs(new_map[asset] - old_map.get(asset, 0.0)) > threshold:
                return True

        return False

    def _set_status(self, status: str, message: str) -> None:
        current = self.repository.load_live_status()
        now = datetime.utcnow().isoformat()

        payload = {
            "status": status,
            "last_run_at": now,
            "last_success_at": current.get("last_success_at"),
            "message": message,
        }

        if status == "ok":
            payload["last_success_at"] = now

        self.repository.save_live_status(payload)

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0