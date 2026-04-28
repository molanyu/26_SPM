from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.routes.form_parser import parse_simple_form
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.core.errors import AppError
from app.modules.identity.constants import (
    IDENTITY_ROLES_READ,
    IDENTITY_ROLES_WRITE,
    IDENTITY_USERS_ROLES_WRITE,
)
from app.modules.identity.dependencies import get_current_admin, require_admin_permission
from app.modules.identity.models.user import User
from app.modules.identity.schemas.role import RoleCreateRequest, RoleUpdateRequest, UserRoleAssignmentRequest

router = APIRouter(prefix="/admin", tags=["admin-portal-identity"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def _is_checked(form: Any, name: str) -> bool:
    return form.get(name) in {"on", "true", "True", "1"}


def _parse_int_list(values: list[str]) -> list[int]:
    parsed: list[int] = []
    for value in values:
        cleaned = value.strip()
        if cleaned:
            parsed.append(int(cleaned))
    return parsed


@router.get(
    "/roles",
    dependencies=[Depends(require_admin_permission(IDENTITY_ROLES_READ))],
)
def roles_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    if not prefers_html(request):
        return page_service.list_roles_payload()
    context = page_service.get_roles_context(request, current_admin)
    return render_page("roles", context)


@router.post(
    "/roles/page",
    dependencies=[Depends(require_admin_permission(IDENTITY_ROLES_WRITE))],
)
async def submit_roles_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    form = await parse_simple_form(request)
    create_form = {
        "name": str(form.get("name", "")),
        "code": str(form.get("code", "")),
        "description": str(form.get("description", "")),
        "is_active": _is_checked(form, "is_active"),
        "permission_ids": form.getlist("permission_ids"),
    }
    try:
        action = str(form.get("form_action", "create"))
        permission_ids = _parse_int_list(form.getlist("permission_ids"))
        payload_data = {
            "name": str(form.get("name", "")),
            "code": str(form.get("code", "")),
            "description": str(form.get("description", "")),
            "is_active": _is_checked(form, "is_active"),
            "permission_ids": permission_ids,
        }
        if action == "update":
            role_id = int(str(form.get("role_id", "")).strip())
            payload = RoleUpdateRequest.model_validate(payload_data)
            page_service.permission_service.update_role(role_id, payload)
            success_message = "Role updated successfully."
        else:
            payload = RoleCreateRequest.model_validate(payload_data)
            page_service.permission_service.create_role(payload)
            success_message = "Role created successfully."
        context = page_service.get_roles_context(
            request,
            current_admin,
            success_message=success_message,
        )
        return render_page("roles", context)
    except (AppError, ValidationError, ValueError) as exc:
        create_form["permission_ids"] = [
            int(value)
            for value in create_form["permission_ids"]
            if str(value).strip().isdigit()
        ]
        context = page_service.get_roles_context(
            request,
            current_admin,
            error_message=page_service.format_exception_message(exc),
            create_form=create_form,
        )
        return render_page("roles", context, status_code=page_service.html_error_status(exc))


@router.get(
    "/users/{user_id}/roles",
    dependencies=[Depends(require_admin_permission(IDENTITY_USERS_ROLES_WRITE))],
)
def user_roles_page(
    user_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    context = page_service.get_user_roles_context(request, current_admin, user_id=user_id)
    return render_page("user_roles", context)


@router.post(
    "/users/{user_id}/roles/page",
    dependencies=[Depends(require_admin_permission(IDENTITY_USERS_ROLES_WRITE))],
)
async def submit_user_roles_page(
    user_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    form = await parse_simple_form(request)
    try:
        payload = UserRoleAssignmentRequest.model_validate(
            {
                "role_ids": _parse_int_list(form.getlist("role_ids")),
            }
        )
        user = page_service.permission_service.assign_roles(user_id, payload.role_ids)
        selected_role_ids = [user_role.role_id for user_role in sorted(user.user_roles, key=lambda item: item.role_id)]
        context = page_service.get_user_roles_context(
            request,
            current_admin,
            user_id=user_id,
            selected_role_ids=selected_role_ids,
            success_message="User roles updated successfully.",
        )
        return render_page("user_roles", context)
    except (AppError, ValidationError, ValueError) as exc:
        context = page_service.get_user_roles_context(
            request,
            current_admin,
            user_id=user_id,
            selected_role_ids=_parse_int_list(form.getlist("role_ids")),
            error_message=page_service.format_exception_message(exc),
        )
        return render_page("user_roles", context, status_code=page_service.html_error_status(exc))
