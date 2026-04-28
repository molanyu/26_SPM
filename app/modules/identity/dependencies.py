from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.modules.identity.services.auth_service import AdminSessionStore, AuthService
from app.modules.identity.services.permission_service import PermissionService
from app.modules.identity.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_admin_session_store(request: Request) -> AdminSessionStore:
    return request.app.state.admin_session_store


def get_auth_service(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthService:
    return AuthService(
        session=db,
        settings=get_settings(request),
        session_store=get_admin_session_store(request),
    )


def get_permission_service(db: Session = Depends(get_db)) -> PermissionService:
    return PermissionService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_current_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    token = credentials.credentials if credentials else None
    return auth_service.get_student_from_token(token)


def get_current_admin(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    cookie_name = get_settings(request).admin_session_cookie_name
    session_token = request.cookies.get(cookie_name)
    return auth_service.get_admin_from_session(session_token)


def require_admin_permission(permission_code: str) -> Callable:
    def _dependency(
        current_admin=Depends(get_current_admin),
        permission_service: PermissionService = Depends(get_permission_service),
    ):
        permission_service.ensure_permission(current_admin.id, permission_code)
        return current_admin

    return _dependency
