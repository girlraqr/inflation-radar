CREATE TABLE IF NOT EXISTS portfolio_performance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL,
    portfolio_value REAL NOT NULL,
    period_return REAL NOT NULL,
    cumulative_return REAL NOT NULL,
    annualized_return REAL NOT NULL,
    annualized_volatility REAL NOT NULL,
    sharpe_ratio REAL NOT NULL,
    max_drawdown REAL NOT NULL,
    hit_rate REAL NOT NULL,
    intelligence_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, snapshot_date)
);