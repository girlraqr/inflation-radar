CREATE TABLE IF NOT EXISTS signal_asset_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    signal TEXT NOT NULL,
    regime TEXT NOT NULL,

    theme TEXT NOT NULL,
    theme_weight REAL NOT NULL,

    asset TEXT NOT NULL,
    asset_weight REAL NOT NULL,

    is_active INTEGER DEFAULT 1,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mapping_signal_regime
ON signal_asset_mapping(signal, regime);