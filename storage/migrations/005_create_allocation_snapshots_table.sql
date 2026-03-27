CREATE TABLE IF NOT EXISTS allocation_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL,
    generated_at TEXT NOT NULL,

    rebalance_required INTEGER,
    rebalance_reason TEXT,

    total_invested_weight REAL,
    cash_weight REAL,
    allocation_hint TEXT,

    weights TEXT,
    positions TEXT,
    signals TEXT,
    meta TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, snapshot_date)
);