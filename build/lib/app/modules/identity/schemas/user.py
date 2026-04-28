from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.modules.identity.schemas.permission import PermissionRead
from app.modules.identity.schemas.role import RoleSummary


class DepartmentRead(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class MenuRead(BaseModel):
    code: str
    label: str


class StudentMeResponse(BaseModel):
    id: int
    name: str
    student_no: str | None = None
    department: DepartmentRead | None = None


class AdminMeResponse(BaseModel):
    id: int
    name: str
    email: str | None = None
    roles: list[RoleSummary] = Field(default_factory=list)
    permissions: list[PermissionRead] = Field(default_factory=list)
    menus: list[MenuRead] = Field(default_factory=list)

