from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class RiskAdjustedSnapshotService:
    """
    Speichert risk-adjusted Portfolio Snapshots
    """

    def __init__(self, snapshot_dir: str | Path = "storage/snapshots/risk_adjusted") -> None:
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def persist_snapshot(
        self,
        user_id: int,
        base_portfolio: Dict[str, Any],
        risk_engine: Dict[str, Any],
        risk_adjusted_portfolio: Dict[str, Any],
    ) -> Dict[str, Any]:

        payload = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "base_portfolio": base_portfolio,
            "risk_engine": risk_engine,
            "risk_adjusted_portfolio": risk_adjusted_portfolio,
        }

        latest_path = self.snapshot_dir / f"user_{user_id}_latest.json"
        history_path = self.snapshot_dir / f"user_{user_id}_history.jsonl"

        # latest
        latest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # history append
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        return payload

    def load_latest_snapshot(self, user_id: int) -> Optional[Dict[str, Any]]:
        path = self.snapshot_dir / f"user_{user_id}_latest.json"
        if not path.exists():
            return None

        return json.loads(path.read_text(encoding="utf-8"))