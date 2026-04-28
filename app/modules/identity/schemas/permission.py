from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PermissionRead(BaseModel):
    id: int
    name: str
    code: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)

