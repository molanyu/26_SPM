from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.admin_portal.routes.dependencies import get_optional_admin_from_session, sanitize_next_path
from app.admin_portal.routes.form_parser import parse_simple_form
from app.admin_portal.services.html_renderer import render_public_page
from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.modules.identity.dependencies import get_auth_service, get_settings
from app.modules.identity.models.user import User
from app.modules.identity.services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["admin-portal-login"])


def _build_error_notice(message: str | None) -> str:
    if not message:
        return ""
    return f'<div class="notice error">{escape(message)}</div>'


def _build_login_context(
    *,
    email: str = "",
    next_path: str | None = None,
    error_message: str | None = None,
) -> dict[str, object]:
    return {
        "email": email,
        "next_path": next_path or "",
        "error_notice_html": _build_error_notice(error_message),
        "bootstrap_hint": (
            "如当前没有管理员账号，请先按项目引导文档配置 "
            "IDENTITY_BOOTSTRAP_ENABLED=true、管理员邮箱和密码，再重新启动应用。"
        ),
    }


def _build_browser_redirect(next_path: str | None) -> RedirectResponse:
    return RedirectResponse(url=next_path or "/admin", status_code=303)


@router.get("/login", name="admin_login_page")
def admin_login_page(
    next: str | None = None,
    current_admin: User | None = Depends(get_optional_admin_from_session),
):
    next_path = sanitize_next_path(next)
    if current_admin is not None:
        return _build_browser_redirect(next_path)
    return render_public_page("login", _build_login_context(next_path=next_path))


@router.post("/login")
async def submit_admin_login(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
):
    form = await parse_simple_form(request)
    email = str(form.get("email", "")).strip()
    password = str(form.get("password", ""))
    next_path = sanitize_next_path(form.get("next"))
    try:
        session_token, _user = auth_service.login_admin(email, password)
    except AuthenticationError as exc:
        return render_public_page(
            "login",
            _build_login_context(
                email=email,
                next_path=next_path,
                error_message=exc.message,
            ),
            status_code=401,
        )

    response = _build_browser_redirect(next_path)
    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.admin_session_cookie_secure,
        samesite=settings.admin_session_cookie_samesite,
        max_age=settings.admin_session_ttl_minutes * 60,
    )
    return response


@router.post("/logout")
def submit_admin_logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
):
    auth_service.logout_admin(request.cookies.get(settings.admin_session_cookie_name))
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key=settings.admin_session_cookie_name)
    return response
