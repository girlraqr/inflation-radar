from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from api.routes.signal_ranking_routes import router as signal_ranking_router
from api.routes.signal_ranking_routes import router as signal_ranking_router
# AUTH
from api.routes.auth.auth_routes import router as auth_router
from auth.dependencies import get_current_user, require_premium_user
from auth.models import User

# ROUTES
from api.routes.backtest_routes import router as backtest_router
from api.routes.live.live_routes import router as live_router
from api.routes.portfolio_routes import router as portfolio_router
from api.routes.mapping_routes import router as mapping_router

# SERVICES
from services.inflation_service import InflationService
from services.regime_service import RegimeService
from services.signal_service import SignalService
from services.forecast_service import ForecastService
from services.ml.training_service import TrainingService

# STORAGE / CONFIG
from storage.training_config import set_mode, get_mode
import storage.history_loader as history_loader


# ---------------------------------------------------
# APP INIT
# ---------------------------------------------------

app = FastAPI(
    title="Inflation Radar API",
    description="Macro Inflation Intelligence Platform",
    version="6.0"
)


# ---------------------------------------------------
# ROUTERS
# ---------------------------------------------------

app.include_router(auth_router)
app.include_router(backtest_router)
app.include_router(live_router)
app.include_router(signal_ranking_router)
app.include_router(portfolio_router)
app.include_router(mapping_router)


# ---------------------------------------------------
# CORS
# ---------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # später einschränken
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
        "version": "6.0",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------
# CORE ENDPOINTS
# ---------------------------------------------------

@app.get("/inflation")
def get_inflation():
    return InflationService.get_real_inflation()


@app.get("/regime")
def get_regime():
    return RegimeService.get_regime()


# ---------------------------------------------------
# 🔐 SIGNALS (FIXED)
# ---------------------------------------------------

@app.get("/signals/free")
def get_free_signals(current_user: User = Depends(get_current_user)):
    signals_dict = signal_service.get_signals()

    # 🔥 FIX: dict → list
    signals_list = list(signals_dict.values())

    return {
        "tier": "free",
        "count": min(2, len(signals_list)),
        "signals": signals_list[:2]
    }


@app.get("/signals/premium")
def get_premium_signals(current_user: User = Depends(require_premium_user)):
    signals_dict = signal_service.get_signals()

    return {
        "tier": "premium",
        "count": len(signals_dict),
        "signals": signals_dict
    }


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