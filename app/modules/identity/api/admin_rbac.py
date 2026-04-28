from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.identity.constants import (
    IDENTITY_PERMISSIONS_READ,
    IDENTITY_ROLES_READ,
    IDENTITY_ROLES_WRITE,
    IDENTITY_USERS_WRITE,
    IDENTITY_USERS_ROLES_WRITE,
)
from app.modules.identity.dependencies import get_permission_service, get_user_service, require_admin_permission
from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.schemas.permission import PermissionRead
from app.modules.identity.schemas.role import (
    RoleCreateRequest,
    RoleRead,
    RoleUpdateRequest,
    UserRoleAssignmentRequest,
)
from app.modules.identity.schemas.user import UserCreateRequest, UserCreateResult
from app.modules.identity.services.permission_service import PermissionService
from app.modules.identity.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["identity-rbac"])


def _build_permission_read(permission: Permission) -> PermissionRead:
    return PermissionRead.model_validate(permission)


def _build_role_read(role: Role) -> RoleRead:
    permissions = [
        _build_permission_read(role_permission.permission)
        for role_permission in sorted(role.role_permissions, key=lambda item: item.permission_id)
    ]
    return RoleRead(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_active=role.is_active,
        permissions=permissions,
    )


def _build_user_result(user: UserCreateResult) -> dict[str, object]:
    return user.model_dump()


@router.get(
    "/roles",
    dependencies=[Depends(require_admin_permission(IDENTITY_ROLES_READ))],
)
def list_roles(permission_service: PermissionService = Depends(get_permission_service)):
    roles = [_build_role_read(role).model_dump() for role in permission_service.list_roles()]
    return {
        "items": roles,
        "total": len(roles),
        "page": 1,
        "page_size": len(roles),
    }


@router.post(
    "/roles",
    dependencies=[Depends(require_admin_permission(IDENTITY_ROLES_WRITE))],
)
def create_role(
    payload: RoleCreateRequest,
    permission_service: PermissionService = Depends(get_permission_service),
):
    role = permission_service.create_role(payload)
    return {
        "success": True,
        "message": "Role created successfully.",
        "data": _build_role_read(role).model_dump(),
    }


@router.put(
    "/roles/{role_id}",
    dependencies=[Depends(require_admin_permission(IDENTITY_ROLES_WRITE))],
)
def update_role(
    role_id: int,
    payload: RoleUpdateRequest,
    permission_service: PermissionService = Depends(get_permission_service),
):
    role = permission_service.update_role(role_id, payload)
    return {
        "success": True,
        "message": "Role updated successfully.",
        "data": _build_role_read(role).model_dump(),
    }


@router.post(
    "/roles/{role_id}/deactivate",
    dependencies=[Depends(require_admin_permission(IDENTITY_ROLES_WRITE))],
)
def deactivate_role(
    role_id: int,
    permission_service: PermissionService = Depends(get_permission_service),
):
    role = permission_service.deactivate_role(role_id)
    return {
        "success": True,
        "message": "Role deactivated successfully.",
        "data": _build_role_read(role).model_dump(),
    }


@router.get(
    "/permissions",
    dependencies=[Depends(require_admin_permission(IDENTITY_PERMISSIONS_READ))],
)
def list_permissions(permission_service: PermissionService = Depends(get_permission_service)):
    permissions = [_build_permission_read(permission).model_dump() for permission in permission_service.list_permissions()]
    return {
        "items": permissions,
        "total": len(permissions),
        "page": 1,
        "page_size": len(permissions),
    }


@router.post(
    "/users",
    dependencies=[Depends(require_admin_permission(IDENTITY_USERS_WRITE))],
)
def create_user(
    payload: UserCreateRequest,
    user_service: UserService = Depends(get_user_service),
):
    user = user_service.create_user(payload)
    return {
        "success": True,
        "message": "用户创建成功。",
        "data": _build_user_result(user),
    }


@router.post(
    "/users/{user_id}/roles",
    dependencies=[Depends(require_admin_permission(IDENTITY_USERS_ROLES_WRITE))],
)
def assign_user_roles(
    user_id: int,
    payload: UserRoleAssignmentRequest,
    permission_service: PermissionService = Depends(get_permission_service),
):
    user = permission_service.assign_roles(user_id, payload.role_ids)
    assigned_role_ids = [user_role.role_id for user_role in sorted(user.user_roles, key=lambda item: item.role_id)]
    return {
        "success": True,
        "message": "User roles updated successfully.",
        "data": {"user_id": user.id, "role_ids": assigned_role_ids},
    }
