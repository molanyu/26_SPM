from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.core.config import Settings
from app.modules.identity.dependencies import (
    get_auth_service,
    get_current_admin,
    get_permission_service,
    get_settings,
)
from app.modules.identity.models.user import User
from app.modules.identity.schemas.auth import AdminLoginRequest
from app.modules.identity.schemas.permission import PermissionRead
from app.modules.identity.schemas.role import RoleSummary
from app.modules.identity.schemas.user import AdminMeResponse, MenuRead
from app.modules.identity.services.auth_service import AuthService
from app.modules.identity.services.menu_service import MenuService
from app.modules.identity.services.permission_service import PermissionService

router = APIRouter(prefix="/admin", tags=["identity-admin"])


def _build_admin_me(user: User, permission_service: PermissionService) -> AdminMeResponse:
    roles = [
        RoleSummary.model_validate(user_role.role)
        for user_role in sorted(user.user_roles, key=lambda item: item.role_id)
        if user_role.role.is_active
    ]
    permissions = [PermissionRead.model_validate(permission) for permission in permission_service.get_user_permissions(user.id)]
    menus = [MenuRead.model_validate(menu) for menu in MenuService().build_menus(permission.code for permission in permissions)]
    return AdminMeResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        roles=roles,
        permissions=permissions,
        menus=menus,
    )


@router.post("/auth/login")
def login_admin(
    payload: AdminLoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    permission_service: PermissionService = Depends(get_permission_service),
    settings: Settings = Depends(get_settings),
):
    session_token, user = auth_service.login_admin(payload.email, payload.password)
    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.admin_session_cookie_secure,
        samesite=settings.admin_session_cookie_samesite,
        max_age=settings.admin_session_ttl_minutes * 60,
    )
    return {
        "success": True,
        "message": "Admin login successful.",
        "data": {"user": _build_admin_me(user, permission_service).model_dump()},
    }


@router.post("/auth/logout")
def logout_admin(
    request: Request,
    response: Response,
    _: User = Depends(get_current_admin),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
):
    auth_service.logout_admin(request.cookies.get(settings.admin_session_cookie_name))
    response.delete_cookie(key=settings.admin_session_cookie_name)
    return {
        "success": True,
        "message": "Admin logout successful.",
        "data": None,
    }


@router.get("/me", response_model=AdminMeResponse)
def get_admin_me(
    current_admin: User = Depends(get_current_admin),
    permission_service: PermissionService = Depends(get_permission_service),
) -> AdminMeResponse:
    return _build_admin_me(current_admin, permission_service)

