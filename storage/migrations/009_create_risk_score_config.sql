CREATE TABLE IF NOT EXISTS risk_score_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 0,

    confidence_weight_strength REAL NOT NULL DEFAULT 0.50,
    confidence_weight_agreement REAL NOT NULL DEFAULT 0.25,
    confidence_weight_breadth REAL NOT NULL DEFAULT 0.25,

    risk_weight_inverse_strength REAL NOT NULL DEFAULT 0.35,
    risk_weight_dispersion REAL NOT NULL DEFAULT 0.20,
    risk_weight_concentration REAL NOT NULL DEFAULT 0.30,
    risk_weight_drawdown REAL NOT NULL DEFAULT 0.15,

    breadth_full_score_at INTEGER NOT NULL DEFAULT 5,
    drawdown_full_penalty_at REAL NOT NULL DEFAULT 0.20,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO risk_score_config (
    profile_name,
    is_active,
    confidence_weight_strength,
    confidence_weight_agreement,
    confidence_weight_breadth,
    risk_weight_inverse_strength,
    risk_weight_dispersion,
    risk_weight_concentration,
    risk_weight_drawdown,
    breadth_full_score_at,
    drawdown_full_penalty_at
) VALUES (
    'default',
    1,
    0.50,
    0.25,
    0.25,
    0.35,
    0.20,
    0.30,
    0.15,
    5,
    0.20
);