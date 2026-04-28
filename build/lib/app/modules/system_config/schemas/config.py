from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SystemConfigRead(BaseModel):
    id: int
    config_key: str
    config_value: int
    value_type: str
    description: str | None = None
    updated_at: datetime


class SystemConfigUpdateRequest(BaseModel):
    config_value: Any
