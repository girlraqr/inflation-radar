from pydantic import BaseModel
from typing import List, Dict


class AssetSignal(BaseModel):
    asset: str
    direction: str
    strength: float
    drivers: List[str]


class SignalsResponse(BaseModel):
    regime: str
    signals: Dict[str, AssetSignal]