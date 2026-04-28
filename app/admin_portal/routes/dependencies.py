from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.modules.identity.dependencies import get_auth_service, get_permission_service, get_settings
from app.modules.identity.models.user import User
from app.modules.identity.services.auth_service import AuthService
from app.modules.identity.services.permission_service import PermissionService


def prefers_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "").lower()


def sanitize_next_path(next_path: object) -> str | None:
    cleaned = str(next_path or "").strip()
    if not cleaned:
        return None
    if not cleaned.startswith("/") or cleaned.startswith("//"):
        return None
    if cleaned.startswith("/admin/login") or cleaned.startswith("/admin/logout"):
        return None
    return cleaned


def build_admin_login_redirect(request: Request) -> RedirectResponse:
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    encoded_target = quote(target, safe="")
    return RedirectResponse(url=f"/admin/login?next={encoded_target}", status_code=303)


def get_optional_admin_from_session(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> User | None:
    try:
        return auth_service.get_admin_from_session(request.cookies.get(settings.admin_session_cookie_name))
    except AuthenticationError:
        return None


def require_admin_portal_permission(permission_code: str) -> Callable:
    def _dependency(
        request: Request,
        auth_service: AuthService = Depends(get_auth_service),
        permission_service: PermissionService = Depends(get_permission_service),
        settings: Settings = Depends(get_settings),
    ) -> User | RedirectResponse:
        try:
            current_admin = auth_service.get_admin_from_session(
                request.cookies.get(settings.admin_session_cookie_name),
            )
        except AuthenticationError:
            if prefers_html(request):
                return build_admin_login_redirect(request)
            raise

        permission_service.ensure_permission(current_admin.id, permission_code)
        return current_admin

    return _dependency
