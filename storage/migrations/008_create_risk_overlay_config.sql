CREATE TABLE IF NOT EXISTS risk_overlay_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 0,

    max_single_asset_weight REAL NOT NULL DEFAULT 0.35,
    max_single_theme_weight REAL NOT NULL DEFAULT 0.60,

    min_cash_weight REAL NOT NULL DEFAULT 0.00,
    max_cash_weight REAL NOT NULL DEFAULT 1.00,
    base_cash_weight REAL NOT NULL DEFAULT 0.00,

    weak_signal_cash_scale REAL NOT NULL DEFAULT 0.25,
    risk_off_cash_weight REAL NOT NULL DEFAULT 0.70,
    risk_off_trigger REAL NOT NULL DEFAULT 0.80,

    max_portfolio_leverage REAL NOT NULL DEFAULT 1.00,
    redistribute_excess_to_cash INTEGER NOT NULL DEFAULT 1,

    risk_off_defensive_asset TEXT NOT NULL DEFAULT 'SHY',
    cash_proxy_asset TEXT NOT NULL DEFAULT 'CASH',

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO risk_overlay_config (
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
) VALUES (
    'default',
    1,
    0.35,
    0.60,
    0.00,
    1.00,
    0.00,
    0.25,
    0.70,
    0.80,
    1.00,
    1,
    'SHY',
    'CASH'
);