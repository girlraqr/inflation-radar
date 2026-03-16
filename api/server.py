from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.inflation_service import get_inflation_data
from services.regime_service import get_regime
from services.signal_service import get_signals
from storage.history_loader import (
    load_history,
    append_snapshot,
    create_snapshot,
)

app = FastAPI(
    title="Inflation Radar API",
    description="Macro Inflation Intelligence Platform",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "Inflation Radar",
        "status": "running",
        "endpoints": [
            "/inflation",
            "/regime",
            "/signals",
            "/history",
            "/snapshot",
            "/health",
        ],
    }


@app.get("/inflation")
def inflation():
    return get_inflation_data()


@app.get("/regime")
def regime():
    return get_regime()


@app.get("/signals")
def signals():
    return get_signals()


@app.get("/history")
def history():
    return {
        "history": load_history()
    }


@app.post("/snapshot")
def snapshot():
    inflation_data = get_inflation_data()
    regime_data = get_regime()
    signals_data = get_signals()

    snapshot_data = create_snapshot(
        real_inflation=inflation_data.get("real_inflation", 0),
        nowcast=inflation_data.get("nowcast_value", 0),
        regime=regime_data.get("regime", "UNKNOWN"),
        gold_signal=signals_data.get("gold_signal", "N/A"),
    )

    append_snapshot(snapshot_data)

    return {
        "status": "saved",
        "snapshot": snapshot_data,
    }


@app.get("/health")
def health():
    return {"status": "ok"}