from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.inflation_service import InflationService
from services.regime_service import RegimeService
from services.signal_service import SignalService
from services.forecast_service import ForecastService

from services.ml.training_service import TrainingService
from storage.training_config import set_mode, get_mode

import storage.history_loader as history_loader


app = FastAPI(
    title="Inflation Radar API",
    description="Macro Inflation Intelligence Platform",
    version="4.2"
)


# ---------------------------------------------------
# CORS für Streamlit Dashboard
# ---------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------
# SERVICES INITIALISIEREN
# ---------------------------------------------------

forecast_service = ForecastService()
signal_service = SignalService()


# ---------------------------------------------------
# Health Check
# ---------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "Inflation Radar API",
        "version": "4.2",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------
# Inflation Endpoints
# ---------------------------------------------------

@app.get("/inflation")
def get_inflation():
    """
    Aktuelle reale Inflation berechnen
    """
    return InflationService.get_real_inflation()


# ---------------------------------------------------
# Regime Engine
# ---------------------------------------------------

@app.get("/regime")
def get_regime():
    """
    Inflation Regime bestimmen
    """
    return RegimeService.get_regime()


# ---------------------------------------------------
# Asset Signals (v2)
# ---------------------------------------------------

@app.get("/signals")
def get_signals():
    """
    Multi-Asset Signals mit Strength Score (v2)
    """
    return signal_service.get_signals()


# ---------------------------------------------------
# Snapshot History
# ---------------------------------------------------

@app.get("/history")
def get_history():
    return history_loader.load_history()


@app.post("/snapshot")
def create_snapshot():
    return history_loader.create_snapshot()


# ---------------------------------------------------
# ML Forecast Engine (Multi-Horizon)
# ---------------------------------------------------

@app.get("/forecast/inflation")
def forecast_inflation():
    """
    ML-basierte Inflationsprognose (1M / 3M / 6M)
    """
    return forecast_service.get_inflation_forecast()


# ---------------------------------------------------
# 🔥 ADMIN: ML TRAINING CONTROL
# ---------------------------------------------------

@app.post("/admin/train")
def trigger_training():
    """
    Manuelles ML Training (Test / Admin Button)
    """
    return TrainingService.run_full_pipeline()


@app.get("/admin/training-mode")
def get_training_mode():
    """
    Aktueller Training Mode (manual / auto)
    """
    return {"mode": get_mode()}


@app.post("/admin/training-mode/{mode}")
def update_training_mode(mode: str):
    """
    Setzt Training Mode:
    - manual
    - auto
    """
    if mode not in ["manual", "auto"]:
        return {"error": "invalid mode"}

    return set_mode(mode)
    
    
# ---------------------------------------------------
# ADMIN: TRAINING CONTROL (VALIDATION)
# ---------------------------------------------------

@app.post("/admin/train/test")
def trigger_test_training():
    """
    Trainiert Modelle, deployt aber nichts
    """
    return TrainingService.run_full_pipeline(deploy=False)


@app.post("/admin/train/real")
def trigger_real_training():
    """
    Trainiert Modelle und deployt nur wenn besser
    """
    return TrainingService.run_full_pipeline(deploy=True)


@app.post("/admin/train/auto-run")
def trigger_auto_training():
    """
    Für Cloud Scheduler gedacht
    """
    return TrainingService.run_training_by_mode()