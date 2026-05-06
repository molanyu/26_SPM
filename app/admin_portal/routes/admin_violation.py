from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.routes.dependencies import require_admin_portal_permission
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.core.errors import AppError, BadRequestError
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ
from app.modules.identity.models.user import User
from app.modules.violation.schemas.violation import ViolationQueryFilters

router = APIRouter(prefix="/admin", tags=["admin-portal-violation"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def _build_filter_state(
    *,
    user_id: int | str | None,
    student_no: str | None,
    room_id: int | str | None,
    date_from: date | None,
    date_to: date | None,
    page: int | str,
    page_size: int | str,
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "student_no": student_no,
        "room_id": room_id,
        "date_from": date_from,
        "date_to": date_to,
        "page": page,
        "page_size": page_size,
    }


def _validation_error_response(page_service: AdminPageService, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "code": "bad_request",
            "message": page_service.format_exception_message(exc),
            "details": jsonable_encoder(exc.errors()),
        },
    )


def _app_error_response(exc: AppError) -> JSONResponse:
    details = exc.details if exc.details is not None else {"message": exc.message}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": details,
        },
    )


def _parse_optional_int(value: str | None, field_name: str) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise BadRequestError(f"{field_name} 必须是数字。") from exc
    if parsed < 1:
        raise BadRequestError(f"{field_name} 必须大于 0。")
    return parsed


def _parse_optional_date(value: str | None, field_name: str) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BadRequestError(f"{field_name} 必须是有效日期。") from exc


def _build_filters_from_raw(
    *,
    user_id: str | None,
    student_no: str | None,
    room_id: str | None,
    date_from: str | None,
    date_to: str | None,
    page: str | None,
    page_size: str | None,
) -> ViolationQueryFilters:
    try:
        return ViolationQueryFilters(
            user_id=_parse_optional_int(user_id, "用户 ID"),
            student_no=student_no,
            room_id=_parse_optional_int(room_id, "自习室 ID"),
            date_from=_parse_optional_date(date_from, "开始日期"),
            date_to=_parse_optional_date(date_to, "结束日期"),
            page=_parse_optional_int(page, "页码") or 1,
            page_size=_parse_optional_int(page_size, "每页条数") or 20,
        )
    except ValidationError as exc:
        error_message = exc.errors()[0]["msg"] if exc.errors() else "违约查询参数不正确。"
        raise BadRequestError(str(error_message)) from exc


@router.get("/violations")
def violations_page(
    request: Request,
    user_id: str | None = None,
    student_no: str | None = None,
    room_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: str | None = "1",
    page_size: str | None = "20",
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_PERMISSIONS_READ)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    wants_html = prefers_html(request)
    try:
        filters = _build_filters_from_raw(
            user_id=user_id,
            student_no=student_no,
            room_id=room_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        if not wants_html:
            return page_service.list_violations_payload(filters)
        context = page_service.get_violations_context(
            request,
            current_admin,
            user_id=filters.user_id,
            student_no=filters.student_no,
            room_id=filters.room_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            page=filters.page,
            page_size=filters.page_size,
        )
        return render_page("violations", context)
    except AppError as exc:
        if not wants_html:
            return _app_error_response(exc)
        filter_state = _build_filter_state(
            user_id=user_id,
            student_no=student_no,
            room_id=room_id,
            date_from=date_from,
            date_to=date_to,
            page=page or "1",
            page_size=page_size or "20",
        )
        context = page_service.build_base_context(
            request,
            current_admin,
            page_title="违约记录查询",
            page_key="violation.records",
            page_intro="按用户、学号、自习室和日期范围查询违约记录，所有筛选条件均可单独使用。",
            error_message=page_service.format_exception_message(exc),
            violations=[],
            total=0,
            filters=filter_state,
        )
        return render_page("violations", context, status_code=page_service.html_error_status(exc))
    except ValidationError as exc:
        if not wants_html:
            return _validation_error_response(page_service, exc)
        context = page_service.build_base_context(
            request,
            current_admin,
            page_title="违约记录查询",
            page_key="violation.records",
            page_intro="按用户、自习室和日期范围查询违约记录，时间范围错误会直接提示。",
            error_message=page_service.format_exception_message(exc),
            violations=[],
            total=0,
            filters=_build_filter_state(
                user_id=user_id,
                student_no=student_no,
                room_id=room_id,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size,
            ),
        )
        return render_page("violations", context, status_code=page_service.html_error_status(exc))
