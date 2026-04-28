from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.admin_portal.routes.dependencies import require_admin_portal_permission
from app.admin_portal.routes.form_parser import parse_simple_form
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.core.errors import AppError
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ, IDENTITY_ROLES_WRITE
from app.modules.identity.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-portal-system-config"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


@router.get("/system-configs")
def system_configs_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_PERMISSIONS_READ)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    if not prefers_html(request):
        return page_service.list_system_configs_payload()
    context = page_service.get_system_configs_context(request, current_admin)
    return render_page("system_configs", context)


@router.post("/system-configs/page")
async def submit_system_configs_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_ROLES_WRITE)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    form = await parse_simple_form(request)
    config_key = str(form.get("config_key", "")).strip()
    raw_value = str(form.get("config_value", ""))
    try:
        page_service.config_service.update_config(config_key, raw_value)
        context = page_service.get_system_configs_context(
            request,
            current_admin,
            success_message="系统参数更新成功。",
        )
        return render_page("system_configs", context)
    except AppError as exc:
        context = page_service.get_system_configs_context(
            request,
            current_admin,
            error_message=page_service.format_exception_message(exc),
        )
        return render_page("system_configs", context, status_code=page_service.html_error_status(exc))
