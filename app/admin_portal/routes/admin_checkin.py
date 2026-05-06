from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.admin_portal.routes.dependencies import require_admin_portal_permission
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.core.errors import AppError, BadRequestError
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-portal-checkin"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


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


@router.get("/checkins")
def checkins_page(
    request: Request,
    room_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: str | None = "1",
    page_size: str | None = "20",
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(ADMIN_PORTAL_ACCESS)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    wants_html = prefers_html(request)
    try:
        resolved_room_id = _parse_optional_int(room_id, "自习室 ID")
        resolved_date_from = _parse_optional_date(date_from, "开始日期")
        resolved_date_to = _parse_optional_date(date_to, "结束日期")
        resolved_page = _parse_optional_int(page, "页码") or 1
        resolved_page_size = _parse_optional_int(page_size, "每页条数") or 20
        if not wants_html:
            current_code = (
                page_service.admin_checkin_service.get_current_dynamic_code(resolved_room_id)
                if resolved_room_id is not None
                else None
            )
            records = page_service.admin_checkin_service.list_records(
                room_id=resolved_room_id,
                date_from=resolved_date_from,
                date_to=resolved_date_to,
                page=resolved_page,
                page_size=resolved_page_size,
            )
            return {
                "rooms": page_service.admin_checkin_service.list_active_rooms(),
                "code": None
                if current_code is None
                else {
                    "room_id": current_code.room_id,
                    "code": current_code.code,
                    "time_slice_start": current_code.time_slice_start,
                    "expires_at": current_code.expires_at,
                    "remaining_seconds": current_code.remaining_seconds,
                },
                "items": records.items,
                "total": records.total,
                "page": records.page,
                "page_size": records.page_size,
            }
        context = page_service.get_checkins_context(
            request,
            current_admin,
            room_id=resolved_room_id,
            date_from=resolved_date_from,
            date_to=resolved_date_to,
            page=resolved_page,
            page_size=resolved_page_size,
        )
        return render_page("checkins", context)
    except AppError as exc:
        if not wants_html:
            return _app_error_response(exc)
        context = page_service.get_checkins_context(
            request,
            current_admin,
            error_message=exc.message,
        )
        return render_page("checkins", context, status_code=exc.status_code)
