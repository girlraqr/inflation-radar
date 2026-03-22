from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class LiveSignalRepository:
    def __init__(self, base_path: str = "storage/cache/live") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.current_signal_path = self.base_path / "current_signal.json"
        self.current_allocation_path = self.base_path / "current_allocation.json"
        self.current_regime_path = self.base_path / "current_regime.json"
        self.live_status_path = self.base_path / "live_status.json"
        self.history_path = self.base_path / "signal_history.json"

    def save_current_signal(self, payload: Dict[str, Any]) -> None:
        self._write_json(self.current_signal_path, payload)

    def load_current_signal(self) -> Dict[str, Any]:
        return self._read_json(self.current_signal_path, default={})

    def save_current_allocation(self, payload: Dict[str, Any]) -> None:
        self._write_json(self.current_allocation_path, payload)

    def load_current_allocation(self) -> Dict[str, Any]:
        return self._read_json(self.current_allocation_path, default={})

    def save_current_regime(self, payload: Dict[str, Any]) -> None:
        self._write_json(self.current_regime_path, payload)

    def load_current_regime(self) -> Dict[str, Any]:
        return self._read_json(self.current_regime_path, default={})

    def save_live_status(self, payload: Dict[str, Any]) -> None:
        self._write_json(self.live_status_path, payload)

    def load_live_status(self) -> Dict[str, Any]:
        return self._read_json(self.live_status_path, default={})

    def append_history_item(self, payload: Dict[str, Any], max_items: int = 500) -> None:
        history = self._read_json(self.history_path, default=[])
        if not isinstance(history, list):
            history = []

        history.append(payload)
        history = history[-max_items:]
        self._write_json(self.history_path, history)

    def load_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        history = self._read_json(self.history_path, default=[])
        if not isinstance(history, list):
            return []
        return history[-limit:][::-1]

    def _write_json(self, path: Path, payload: Any) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return default