from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import BadRequestError
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.dependencies import require_admin_permission
from app.modules.reservation.schemas.reservation import (
    AdminReservationCancelRequest,
    AdminReservationCreateRequest,
    AdminReservationQueryFilters,
)
from app.modules.reservation.services.query_service import ReservationQueryService
from app.modules.reservation.services.reservation_service import ReservationService, build_reservation_write_data

router = APIRouter(
    prefix="/admin",
    tags=["reservation-admin"],
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    return ReservationService(db)


def get_reservation_query_service(db: Session = Depends(get_db)) -> ReservationQueryService:
    return ReservationQueryService(db)


def _build_query_filters(
    *,
    user_id: int | None,
    room_id: int | None,
    seat_id: int | None,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    page_size: int,
) -> AdminReservationQueryFilters:
    try:
        return AdminReservationQueryFilters(
            user_id=user_id,
            room_id=room_id,
            seat_id=seat_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
    except ValidationError as exc:
        error_message = exc.errors()[0]["msg"] if exc.errors() else "Invalid reservation query parameters."
        raise BadRequestError(error_message) from exc


@router.get("/reservations")
def list_admin_reservations(
    user_id: int | None = None,
    room_id: int | None = None,
    seat_id: int | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    reservation_query_service: ReservationQueryService = Depends(get_reservation_query_service),
):
    filters = _build_query_filters(
        user_id=user_id,
        room_id=room_id,
        seat_id=seat_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    result = reservation_query_service.list_admin_records(filters)
    return {
        "items": [item.model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


@router.post("/reservations")
def create_admin_reservation(
    payload: AdminReservationCreateRequest,
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    reservation = reservation_service.create_admin_reservation(payload)
    return {
        "success": True,
        "message": "Reservation created successfully.",
        "data": build_reservation_write_data(reservation).model_dump(),
    }


@router.post("/reservations/{reservation_id}/cancel")
def cancel_admin_reservation(
    reservation_id: int,
    payload: AdminReservationCancelRequest,
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    reservation = reservation_service.cancel_admin_reservation(reservation_id, payload)
    return {
        "success": True,
        "message": "Reservation cancelled successfully.",
        "data": build_reservation_write_data(reservation).model_dump(),
    }
