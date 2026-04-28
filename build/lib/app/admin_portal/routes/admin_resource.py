from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.routes.form_parser import parse_simple_form
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.core.errors import AppError
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.dependencies import get_current_admin, require_admin_permission
from app.modules.identity.models.user import User
from app.modules.resource.schemas.room import RoomCreateRequest, RoomUpdateRequest
from app.modules.resource.schemas.seat import SeatCreateRequest, SeatUpdateRequest

router = APIRouter(prefix="/admin", tags=["admin-portal-resource"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def _is_checked(form: Any, name: str) -> bool:
    return form.get(name) in {"on", "true", "True", "1"}


def _optional_int(value: object) -> int | None:
    cleaned = str(value or "").strip()
    return int(cleaned) if cleaned else None


@router.get(
    "/rooms",
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)
def rooms_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    if not prefers_html(request):
        return page_service.list_rooms_payload()
    context = page_service.get_rooms_context(request, current_admin)
    return render_page("rooms", context)


@router.post(
    "/rooms/page",
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)
async def submit_rooms_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    form = await parse_simple_form(request)
    create_form = {
        "name": str(form.get("name", "")),
        "location": str(form.get("location", "")),
        "department_id": str(form.get("department_id", "")),
        "is_department_only": _is_checked(form, "is_department_only"),
        "is_active": _is_checked(form, "is_active"),
        "open_time": str(form.get("open_time", "")),
        "close_time": str(form.get("close_time", "")),
    }
    try:
        action = str(form.get("form_action", "create"))
        payload_data = {
            "name": str(form.get("name", "")),
            "location": str(form.get("location", "")),
            "department_id": _optional_int(form.get("department_id")),
            "is_department_only": _is_checked(form, "is_department_only"),
            "is_active": _is_checked(form, "is_active"),
            "open_time": str(form.get("open_time", "")),
            "close_time": str(form.get("close_time", "")),
        }
        if action == "update":
            room_id = int(str(form.get("room_id", "")).strip())
            payload = RoomUpdateRequest.model_validate(payload_data)
            page_service.room_service.update_room(room_id, payload)
            success_message = "Room updated successfully."
        elif action == "deactivate":
            room_id = int(str(form.get("room_id", "")).strip())
            page_service.room_service.deactivate_room(room_id)
            success_message = "Room deactivated successfully."
        else:
            payload = RoomCreateRequest.model_validate(payload_data)
            page_service.room_service.create_room(payload)
            success_message = "Room created successfully."
        context = page_service.get_rooms_context(
            request,
            current_admin,
            success_message=success_message,
        )
        return render_page("rooms", context)
    except (AppError, ValidationError, ValueError) as exc:
        context = page_service.get_rooms_context(
            request,
            current_admin,
            error_message=page_service.format_exception_message(exc),
            create_form=create_form,
        )
        return render_page("rooms", context, status_code=page_service.html_error_status(exc))


@router.get(
    "/seats",
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)
def seats_page(
    request: Request,
    room_id: int | None = Query(default=None),
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    if not prefers_html(request):
        return page_service.list_seats_payload(room_id=room_id)
    context = page_service.get_seats_context(request, current_admin, room_id=room_id)
    return render_page("seats", context)


@router.post(
    "/seats/page",
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)
async def submit_seats_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    form = await parse_simple_form(request)
    create_form = {
        "room_id": str(form.get("room_id", "")),
        "seat_code": str(form.get("seat_code", "")),
        "seat_label": str(form.get("seat_label", "")),
        "is_active": _is_checked(form, "is_active"),
        "is_window_side": _is_checked(form, "is_window_side"),
        "has_power_socket": _is_checked(form, "has_power_socket"),
        "has_track_socket": _is_checked(form, "has_track_socket"),
    }
    selected_room_id = _optional_int(form.get("filter_room_id")) or _optional_int(form.get("room_id"))
    try:
        action = str(form.get("form_action", "create"))
        payload_data = {
            "room_id": int(str(form.get("room_id", "")).strip()),
            "seat_code": str(form.get("seat_code", "")),
            "seat_label": str(form.get("seat_label", "")),
            "is_active": _is_checked(form, "is_active"),
            "is_window_side": _is_checked(form, "is_window_side"),
            "has_power_socket": _is_checked(form, "has_power_socket"),
            "has_track_socket": _is_checked(form, "has_track_socket"),
        }
        if action == "update":
            seat_id = int(str(form.get("seat_id", "")).strip())
            payload = SeatUpdateRequest.model_validate(payload_data)
            page_service.seat_service.update_seat(seat_id, payload)
            success_message = "Seat updated successfully."
        elif action == "deactivate":
            seat_id = int(str(form.get("seat_id", "")).strip())
            page_service.seat_service.deactivate_seat(seat_id)
            success_message = "Seat deactivated successfully."
        else:
            payload = SeatCreateRequest.model_validate(payload_data)
            page_service.seat_service.create_seat(payload)
            success_message = "Seat created successfully."
        context = page_service.get_seats_context(
            request,
            current_admin,
            room_id=selected_room_id,
            success_message=success_message,
        )
        return render_page("seats", context)
    except (AppError, ValidationError, ValueError) as exc:
        context = page_service.get_seats_context(
            request,
            current_admin,
            room_id=selected_room_id,
            error_message=page_service.format_exception_message(exc),
            create_form=create_form,
        )
        return render_page("seats", context, status_code=page_service.html_error_status(exc))
