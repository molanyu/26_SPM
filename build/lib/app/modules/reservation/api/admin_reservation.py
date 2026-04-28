from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.dependencies import require_admin_permission
from app.modules.reservation.schemas.reservation import AdminReservationCancelRequest, AdminReservationCreateRequest
from app.modules.reservation.services.reservation_service import ReservationService, build_reservation_write_data

router = APIRouter(
    prefix="/admin",
    tags=["reservation-admin"],
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    return ReservationService(db)


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
