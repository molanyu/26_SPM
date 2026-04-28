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
from app.modules.identity.constants import (
    ADMIN_PORTAL_ACCESS,
    IDENTITY_ROLES_READ,
    IDENTITY_ROLES_WRITE,
    IDENTITY_USERS_WRITE,
    IDENTITY_USERS_ROLES_WRITE,
)
from app.modules.identity.models.user import User
from app.modules.identity.schemas.role import RoleCreateRequest, RoleUpdateRequest, UserRoleAssignmentRequest
from app.modules.identity.schemas.user import UserCreateRequest

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


def _parse_optional_int(value: object) -> int | None:
    cleaned = str(value or "").strip()
    if not cleaned:
        return None
    return int(cleaned)


@router.get("/roles")
def roles_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_ROLES_READ)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    if not prefers_html(request):
        return page_service.list_roles_payload()

    edit_role_id: int | None = None
    error_message: str | None = None
    raw_edit_role_id = request.query_params.get("edit_role_id")
    if raw_edit_role_id:
        try:
            edit_role_id = _parse_optional_int(raw_edit_role_id)
        except ValueError:
            error_message = "要编辑的角色编号无效，请重新选择。"

    context = page_service.get_roles_context(
        request,
        current_admin,
        edit_role_id=edit_role_id,
        error_message=error_message,
    )
    return render_page("roles", context)


@router.post("/roles/page")
async def submit_roles_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(ADMIN_PORTAL_ACCESS)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    form = await parse_simple_form(request)
    action = str(form.get("form_action", "create"))

    if action == "locate_user_roles":
        target_user = str(form.get("target_user", ""))
        try:
            page_service.permission_service.ensure_permission(current_admin.id, IDENTITY_USERS_ROLES_WRITE)
            user = page_service.permission_service.resolve_user_for_role_assignment(target_user)
            return RedirectResponse(url=f"/admin/users/{user.id}/roles", status_code=303)
        except (AppError, ValidationError, ValueError) as exc:
            context = page_service.get_roles_context(
                request,
                current_admin,
                error_message=page_service.format_exception_message(exc),
                target_lookup_value=target_user,
            )
            return render_page("roles", context, status_code=page_service.html_error_status(exc))

    if action == "deactivate":
        try:
            page_service.permission_service.ensure_permission(current_admin.id, IDENTITY_ROLES_WRITE)
            role_id = _parse_optional_int(form.get("role_id"))
            if role_id is None:
                raise ValueError("请选择要停用的角色。")
            page_service.permission_service.deactivate_role(role_id)
            context = page_service.get_roles_context(
                request,
                current_admin,
                success_message="角色已停用。",
            )
            return render_page("roles", context)
        except (AppError, ValidationError, ValueError) as exc:
            context = page_service.get_roles_context(
                request,
                current_admin,
                error_message=page_service.format_exception_message(exc),
            )
            return render_page("roles", context, status_code=page_service.html_error_status(exc))

    create_form = {
        "name": str(form.get("name", "")),
        "code": str(form.get("code", "")),
        "description": str(form.get("description", "")),
        "is_active": _is_checked(form, "is_active"),
        "permission_ids": form.getlist("permission_ids"),
    }
    edit_form = {
        "role_id": str(form.get("role_id", "")),
        **create_form,
    }

    try:
        page_service.permission_service.ensure_permission(current_admin.id, IDENTITY_ROLES_WRITE)
        edit_role_id = _parse_optional_int(edit_form.get("role_id"))
        permission_ids = _parse_int_list(form.getlist("permission_ids"))
        payload_data = {
            "name": str(form.get("name", "")),
            "code": str(form.get("code", "")),
            "description": str(form.get("description", "")),
            "is_active": _is_checked(form, "is_active"),
            "permission_ids": permission_ids,
        }
        if action == "update":
            if edit_role_id is None:
                raise ValueError("请选择要更新的角色。")
            payload = RoleUpdateRequest.model_validate(payload_data)
            page_service.permission_service.update_role(edit_role_id, payload)
            context = page_service.get_roles_context(
                request,
                current_admin,
                edit_role_id=edit_role_id,
                success_message="角色已更新。",
            )
        else:
            payload = RoleCreateRequest.model_validate(payload_data)
            page_service.permission_service.create_role(payload)
            context = page_service.get_roles_context(
                request,
                current_admin,
                success_message="角色已创建。",
            )
        return render_page("roles", context)
    except (AppError, ValidationError, ValueError) as exc:
        if action == "update":
            context = page_service.get_roles_context(
                request,
                current_admin,
                error_message=page_service.format_exception_message(exc),
                edit_role_id=edit_role_id if "edit_role_id" in locals() else None,
                edit_form=edit_form,
            )
        else:
            context = page_service.get_roles_context(
                request,
                current_admin,
                error_message=page_service.format_exception_message(exc),
                create_form=create_form,
            )
        return render_page("roles", context, status_code=page_service.html_error_status(exc))


@router.get("/users/new")
def user_create_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_USERS_WRITE)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    context = page_service.get_user_create_context(request, current_admin)
    return render_page("user_create", context)


@router.post("/users/new/page")
async def submit_user_create_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_USERS_WRITE)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    form = await parse_simple_form(request)
    create_form = {
        "account_type": str(form.get("account_type", "student")),
        "name": str(form.get("name", "")),
        "student_no": str(form.get("student_no", "")),
        "email": str(form.get("email", "")),
        "notification_email": str(form.get("notification_email", "")),
        "password": str(form.get("password", "")),
        "department_id": str(form.get("department_id", "")),
        "is_active": _is_checked(form, "is_active"),
    }
    try:
        payload = UserCreateRequest.model_validate(
            {
                "account_type": create_form["account_type"],
                "name": create_form["name"],
                "student_no": create_form["student_no"] or None,
                "email": create_form["email"] or None,
                "notification_email": create_form["notification_email"] or None,
                "password": create_form["password"],
                "department_id": _parse_optional_int(create_form["department_id"]),
                "is_active": create_form["is_active"],
            }
        )
        created_user = page_service.user_service.create_user(payload)
        success_message = (
            "管理员账号已创建，请继续分配角色。"
            if created_user.account_type == "admin"
            else "学生账号已创建。"
        )
        context = page_service.get_user_create_context(
            request,
            current_admin,
            success_message=success_message,
            created_user=created_user,
        )
        return render_page("user_create", context)
    except (AppError, ValidationError, ValueError) as exc:
        context = page_service.get_user_create_context(
            request,
            current_admin,
            error_message=page_service.format_exception_message(exc),
            create_form=create_form,
        )
        return render_page("user_create", context, status_code=page_service.html_error_status(exc))


@router.get("/users/{user_id}/roles")
def user_roles_page(
    user_id: int,
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_USERS_ROLES_WRITE)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    context = page_service.get_user_roles_context(request, current_admin, user_id=user_id)
    return render_page("user_roles", context)


@router.post("/users/{user_id}/roles/page")
async def submit_user_roles_page(
    user_id: int,
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_USERS_ROLES_WRITE)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    form = await parse_simple_form(request)
    action = str(form.get("form_action", "assign"))
    if action == "locate_user_roles":
        target_user = str(form.get("target_user", ""))
        try:
            user = page_service.permission_service.resolve_user_for_role_assignment(target_user)
            return RedirectResponse(url=f"/admin/users/{user.id}/roles", status_code=303)
        except (AppError, ValidationError, ValueError) as exc:
            context = page_service.get_user_roles_context(
                request,
                current_admin,
                user_id=user_id,
                error_message=page_service.format_exception_message(exc),
                target_lookup_value=target_user,
            )
            return render_page("user_roles", context, status_code=page_service.html_error_status(exc))
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
            success_message="用户角色已更新。",
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
