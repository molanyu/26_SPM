from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.routes.dependencies import require_admin_portal_permission
from app.admin_portal.routes.form_parser import parse_simple_form
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService
from app.core.database import get_db
from app.core.errors import AppError
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.models.user import User
from app.modules.reservation.schemas.reservation import AdminReservationCancelRequest, AdminReservationCreateRequest
from app.modules.reservation.services.reservation_service import ReservationService, build_reservation_write_data

router = APIRouter(prefix="/admin", tags=["admin-portal-reservation"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    return ReservationService(db)


@router.get("/reservations/records")
def reservation_records_page(
    request: Request,
    user_id: int | None = None,
    room_id: int | None = None,
    seat_id: int | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(ADMIN_PORTAL_ACCESS)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    try:
        context = page_service.get_reservation_records_context(
            request,
            current_admin,
            user_id=user_id,
            room_id=room_id,
            seat_id=seat_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        return render_page("reservation_records", context)
    except ValidationError as exc:
        context = page_service.build_base_context(
            request,
            current_admin,
            page_title="预约记录查询",
            page_key="reservation.records",
            page_intro="按用户、房间、座位、状态和日期范围筛选预约记录，查询结果直接复用公开预约查询服务。",
            error_message=page_service.format_exception_message(exc),
            reservations=[],
            total=0,
            filters={
                "user_id": user_id,
                "room_id": room_id,
                "seat_id": seat_id,
                "status": status,
                "date_from": date_from,
                "date_to": date_to,
                "page": page,
                "page_size": page_size,
            },
        )
        return render_page("reservation_records", context, status_code=page_service.html_error_status(exc))


@router.get("/reservations/actions")
def reservation_actions_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(ADMIN_PORTAL_ACCESS)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    context = page_service.get_reservation_actions_context(request, current_admin)
    return render_page("reservation_actions", context)


@router.post("/reservations/actions/page")
async def submit_reservation_actions_page(
    request: Request,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(ADMIN_PORTAL_ACCESS)),
    reservation_service: ReservationService = Depends(get_reservation_service),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    form = await parse_simple_form(request)
    create_form = {
        "user_id": str(form.get("user_id", "")),
        "seat_id": str(form.get("seat_id", "")),
        "start_time": str(form.get("start_time", "")),
        "end_time": str(form.get("end_time", "")),
    }
    cancel_form = {
        "reservation_id": str(form.get("reservation_id", "")),
        "reason": str(form.get("reason", "")),
    }
    try:
        action = str(form.get("form_action", "create"))
        if action == "cancel":
            payload = AdminReservationCancelRequest.model_validate(
                {
                    "reason": str(form.get("reason", "")) or None,
                }
            )
            reservation = reservation_service.cancel_admin_reservation(
                int(str(form.get("reservation_id", "")).strip()),
                payload,
            )
            context = page_service.get_reservation_actions_context(
                request,
                current_admin,
                success_message="预约已取消。",
                cancel_result=build_reservation_write_data(reservation).model_dump(),
                create_form=create_form,
                cancel_form=cancel_form,
            )
            return render_page("reservation_actions", context)

        payload = AdminReservationCreateRequest.model_validate(
            {
                "user_id": int(str(form.get("user_id", "")).strip()),
                "seat_id": int(str(form.get("seat_id", "")).strip()),
                "start_time": str(form.get("start_time", "")),
                "end_time": str(form.get("end_time", "")),
            }
        )
        reservation = reservation_service.create_admin_reservation(payload)
        context = page_service.get_reservation_actions_context(
            request,
            current_admin,
            success_message="预约创建成功。",
            create_result=build_reservation_write_data(reservation).model_dump(),
            create_form=create_form,
            cancel_form=cancel_form,
        )
        return render_page("reservation_actions", context)
    except (AppError, ValidationError, ValueError) as exc:
        context = page_service.get_reservation_actions_context(
            request,
            current_admin,
            error_message=page_service.format_exception_message(exc),
            create_form=create_form,
            cancel_form=cancel_form,
        )
        return render_page("reservation_actions", context, status_code=page_service.html_error_status(exc))
