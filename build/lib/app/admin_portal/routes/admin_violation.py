from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ
from app.modules.identity.dependencies import get_current_admin, require_admin_permission
from app.modules.identity.models.user import User
from app.modules.violation.schemas.violation import ViolationQueryFilters

router = APIRouter(prefix="/admin", tags=["admin-portal-violation"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def _build_filter_state(
    *,
    user_id: int | None,
    room_id: int | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    page_size: int,
) -> dict[str, object]:
    return {
        "user_id": user_id,
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


@router.get(
    "/violations",
    dependencies=[Depends(require_admin_permission(IDENTITY_PERMISSIONS_READ))],
)
def violations_page(
    request: Request,
    user_id: int | None = None,
    room_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    wants_html = prefers_html(request)
    try:
        filters = ViolationQueryFilters(
            user_id=user_id,
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
            user_id=user_id,
            room_id=room_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        return render_page("violations", context)
    except ValidationError as exc:
        if not wants_html:
            return _validation_error_response(page_service, exc)
        context = page_service.build_base_context(
            request,
            current_admin,
            page_title="Violation Records",
            page_key="violation.records",
            error_message=page_service.format_exception_message(exc),
            violations=[],
            total=0,
            filters=_build_filter_state(
                user_id=user_id,
                room_id=room_id,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size,
            ),
        )
        return render_page("violations", context, status_code=page_service.html_error_status(exc))
