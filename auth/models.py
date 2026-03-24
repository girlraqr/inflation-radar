from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class User:
    id: int
    email: str
    password_hash: str
    full_name: Optional[str]
    role: str
    subscription_tier: str
    is_active: bool
    created_at: str
    updated_at: str