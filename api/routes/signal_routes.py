from fastapi import APIRouter
from services.signal_service import SignalService

router = APIRouter()
service = SignalService()


@router.get("/signals")
def get_signals():
    return service.get_signals()