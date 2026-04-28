from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.modules.identity.schemas.permission import PermissionRead


class RoleSummary(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class RoleRead(RoleSummary):
    description: str | None = None
    is_active: bool
    permissions: list[PermissionRead] = Field(default_factory=list)


class RoleCreateRequest(BaseModel):
    name: str
    code: str
    description: str | None = None
    is_active: bool = True
    permission_ids: list[int] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: str
    code: str
    description: str | None = None
    is_active: bool = True
    permission_ids: list[int] = Field(default_factory=list)


class UserRoleAssignmentRequest(BaseModel):
    role_ids: list[int] = Field(default_factory=list)

