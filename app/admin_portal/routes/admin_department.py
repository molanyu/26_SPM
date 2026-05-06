from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.routes.dependencies import require_admin_portal_permission
from app.admin_portal.routes.form_parser import parse_simple_form
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.core.errors import AppError
from app.modules.identity.constants import IDENTITY_DEPARTMENTS_WRITE
from app.modules.identity.models.user import User
from app.modules.identity.schemas.department import DepartmentCreateRequest

router = APIRouter(prefix="/admin", tags=["admin-portal-departments"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def _is_checked(form: Any, name: str) -> bool:
    return form.get(name) in {"on", "true", "True", "1"}


@router.get("/departments")
def departments_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_DEPARTMENTS_WRITE)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    if not prefers_html(request):
        return page_service.list_departments_payload()
    context = page_service.get_departments_context(request, current_admin)
    return render_page("departments", context)


@router.post("/departments/page")
async def submit_departments_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_DEPARTMENTS_WRITE)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    form = await parse_simple_form(request)
    action = str(form.get("form_action", "create"))
    create_form = {
        "name": str(form.get("name", "")),
        "code": str(form.get("code", "")),
        "is_active": _is_checked(form, "is_active"),
    }
    try:
        if action == "activate":
            department_id = int(str(form.get("department_id", "")).strip())
            page_service.department_service.activate_department(department_id)
            success_message = "院系已启用。"
        elif action == "deactivate":
            department_id = int(str(form.get("department_id", "")).strip())
            page_service.department_service.deactivate_department(department_id)
            success_message = "院系已停用。"
        else:
            payload = DepartmentCreateRequest.model_validate(create_form)
            page_service.department_service.create_department(payload)
            success_message = "院系创建成功。"

        context = page_service.get_departments_context(
            request,
            current_admin,
            success_message=success_message,
        )
        return render_page("departments", context)
    except (AppError, ValidationError, ValueError) as exc:
        context = page_service.get_departments_context(
            request,
            current_admin,
            error_message=page_service.format_exception_message(exc),
            create_form=create_form,
        )
        return render_page("departments", context, status_code=page_service.html_error_status(exc))
