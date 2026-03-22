from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.inflation_service import InflationService
from services.regime_service import RegimeService
from services.signal_service import SignalService
from services.forecast_service import ForecastService

from services.ml.training_service import TrainingService
from storage.training_config import set_mode, get_mode
from api.routes.backtest_routes import router as backtest_router

# >>> NEU: LIVE ROUTER
from api.routes.live.live_routes import router as live_router

import storage.history_loader as history_loader


# ---------------------------------------------------
# APP INIT
# ---------------------------------------------------

app = FastAPI(
    title="Inflation Radar API",
    description="Macro Inflation Intelligence Platform",
    version="5.0"   # <-- Version erhöht (Go-Live Phase)
)

# bestehende Router
app.include_router(backtest_router)

# >>> NEU: Live Signal API
app.include_router(live_router)


# ---------------------------------------------------
# CORS
# ---------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # später einschränken!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------
# SERVICES
# ---------------------------------------------------

forecast_service = ForecastService()
signal_service = SignalService()


# ---------------------------------------------------
# HEALTH
# ---------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "Inflation Radar API",
        "version": "5.0",
        "status": "running",
        "modules": [
            "inflation",
            "regime",
            "signals",
            "forecast",
            "backtest",
            "live"
        ]
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "live_system": "enabled"
    }


# ---------------------------------------------------
# CORE ENDPOINTS
# ---------------------------------------------------

@app.get("/inflation")
def get_inflation():
    return InflationService.get_real_inflation()


@app.get("/regime")
def get_regime():
    return RegimeService.get_regime()


@app.get("/signals")
def get_signals():
    return signal_service.get_signals()


# ---------------------------------------------------
# LIVE (NEU)
# ---------------------------------------------------
# Alle Endpoints liegen jetzt unter:
# /live/current
# /live/allocation/current
# /live/regime/current
# /live/status
# /live/history
# /live/refresh
#
# (definiert in api/routes/live/live_routes.py)


# ---------------------------------------------------
# HISTORY
# ---------------------------------------------------

@app.get("/history")
def get_history():
    return history_loader.load_history()


@app.post("/snapshot")
def create_snapshot():
    return history_loader.create_snapshot()


# ---------------------------------------------------
# FORECAST
# ---------------------------------------------------

@app.get("/forecast/inflation")
def forecast_inflation():
    return forecast_service.get_inflation_forecast()


# ---------------------------------------------------
# ADMIN
# ---------------------------------------------------

@app.post("/admin/train")
def trigger_training():
    return TrainingService.run_full_pipeline()


@app.get("/admin/training-mode")
def get_training_mode():
    return {"mode": get_mode()}


@app.post("/admin/training-mode/{mode}")
def update_training_mode(mode: str):
    if mode not in ["manual", "auto"]:
        return {"error": "invalid mode"}
    return set_mode(mode)


@app.post("/admin/train/test")
def trigger_test_training():
    return TrainingService.run_full_pipeline(deploy=False)


@app.post("/admin/train/real")
def trigger_real_training():
    return TrainingService.run_full_pipeline(deploy=True)


@app.post("/admin/train/auto-run")
def trigger_auto_training():
    return TrainingService.run_training_by_mode()