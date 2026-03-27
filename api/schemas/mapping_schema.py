from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class MappingCreateRequest(BaseModel):
    signal: str
    regime: str
    theme: str
    theme_weight: float
    asset: str
    asset_weight: float


class MappingUpdateRequest(BaseModel):
    theme_weight: Optional[float] = None
    asset_weight: Optional[float] = None
    is_active: Optional[int] = None


class MappingBulkCreateRequest(BaseModel):
    signal: str
    regime: str
    rows: List[MappingCreateRequest]


class MappingResponse(BaseModel):
    id: int
    signal: str
    regime: str
    theme: str
    theme_weight: float
    asset: str
    asset_weight: float
    is_active: int
    created_at: Optional[str] = None