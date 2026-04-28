from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.routes.form_parser import parse_simple_form
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService
from app.core.database import get_db
from app.core.errors import AppError
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.dependencies import get_current_admin, require_admin_permission
from app.modules.identity.models.user import User
from app.modules.reservation.schemas.reservation import AdminReservationCancelRequest, AdminReservationCreateRequest
from app.modules.reservation.services.reservation_service import ReservationService, build_reservation_write_data

router = APIRouter(prefix="/admin", tags=["admin-portal-reservation"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    return ReservationService(db)


@router.get(
    "/reservations/actions",
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)
def reservation_actions_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    context = page_service.get_reservation_actions_context(request, current_admin)
    return render_page("reservation_actions", context)


@router.post(
    "/reservations/actions/page",
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)
async def submit_reservation_actions_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    reservation_service: ReservationService = Depends(get_reservation_service),
    page_service: AdminPageService = Depends(get_page_service),
):
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
                success_message="Reservation cancelled successfully.",
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
            success_message="Reservation created successfully.",
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
