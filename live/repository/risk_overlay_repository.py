from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_DB_PATH = Path("storage/app.db")


class RiskOverlayRepository:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_active_config(self) -> Optional[Dict[str, Any]]:
        query = """
            SELECT *
            FROM risk_overlay_config
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """
        with self._connect() as connection:
            row = connection.execute(query).fetchone()
            return dict(row) if row else None

    def get_config_by_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT *
            FROM risk_overlay_config
            WHERE profile_name = ?
            LIMIT 1
        """
        with self._connect() as connection:
            row = connection.execute(query, (profile_name,)).fetchone()
            return dict(row) if row else None

    def upsert_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_config_by_profile(payload["profile_name"])

        if existing:
            query = """
                UPDATE risk_overlay_config
                SET
                    is_active = ?,
                    max_single_asset_weight = ?,
                    max_single_theme_weight = ?,
                    min_cash_weight = ?,
                    max_cash_weight = ?,
                    base_cash_weight = ?,
                    weak_signal_cash_scale = ?,
                    risk_off_cash_weight = ?,
                    risk_off_trigger = ?,
                    max_portfolio_leverage = ?,
                    redistribute_excess_to_cash = ?,
                    risk_off_defensive_asset = ?,
                    cash_proxy_asset = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE profile_name = ?
            """
            values = (
                int(payload["is_active"]),
                payload["max_single_asset_weight"],
                payload["max_single_theme_weight"],
                payload["min_cash_weight"],
                payload["max_cash_weight"],
                payload["base_cash_weight"],
                payload["weak_signal_cash_scale"],
                payload["risk_off_cash_weight"],
                payload["risk_off_trigger"],
                payload["max_portfolio_leverage"],
                int(payload["redistribute_excess_to_cash"]),
                payload["risk_off_defensive_asset"],
                payload["cash_proxy_asset"],
                payload["profile_name"],
            )
            with self._connect() as connection:
                connection.execute(query, values)
                connection.commit()
        else:
            query = """
                INSERT INTO risk_overlay_config (
                    profile_name,
                    is_active,
                    max_single_asset_weight,
                    max_single_theme_weight,
                    min_cash_weight,
                    max_cash_weight,
                    base_cash_weight,
                    weak_signal_cash_scale,
                    risk_off_cash_weight,
                    risk_off_trigger,
                    max_portfolio_leverage,
                    redistribute_excess_to_cash,
                    risk_off_defensive_asset,
                    cash_proxy_asset
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                payload["profile_name"],
                int(payload["is_active"]),
                payload["max_single_asset_weight"],
                payload["max_single_theme_weight"],
                payload["min_cash_weight"],
                payload["max_cash_weight"],
                payload["base_cash_weight"],
                payload["weak_signal_cash_scale"],
                payload["risk_off_cash_weight"],
                payload["risk_off_trigger"],
                payload["max_portfolio_leverage"],
                int(payload["redistribute_excess_to_cash"]),
                payload["risk_off_defensive_asset"],
                payload["cash_proxy_asset"],
            )
            with self._connect() as connection:
                connection.execute(query, values)
                connection.commit()

        if payload["is_active"]:
            self.set_active_profile(payload["profile_name"])

        saved = self.get_config_by_profile(payload["profile_name"])
        if saved is None:
            raise RuntimeError("Risk overlay config could not be saved.")
        return saved

    def set_active_profile(self, profile_name: str) -> Dict[str, Any]:
        with self._connect() as connection:
            connection.execute("UPDATE risk_overlay_config SET is_active = 0")
            connection.execute(
                "UPDATE risk_overlay_config SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE profile_name = ?",
                (profile_name,),
            )
            connection.commit()

        config = self.get_config_by_profile(profile_name)
        if config is None:
            raise ValueError(f"Risk overlay profile '{profile_name}' not found.")
        return config