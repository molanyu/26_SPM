from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_student
from app.modules.identity.models.user import User
from app.modules.reservation.schemas.reservation import (
    SeatAvailabilityQueryParams,
    StudentReservationCancelRequest,
    StudentReservationCreateRequest,
)
from app.modules.reservation.services.availability_service import AvailabilityService
from app.modules.reservation.services.history_service import HistoryService
from app.modules.reservation.services.reservation_service import ReservationService, build_reservation_write_data

router = APIRouter(prefix="/student", tags=["reservation-student"])


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    return ReservationService(db)


def get_history_service(db: Session = Depends(get_db)) -> HistoryService:
    return HistoryService(db)


def get_availability_service(db: Session = Depends(get_db)) -> AvailabilityService:
    return AvailabilityService(db)


@router.post("/reservations")
def create_student_reservation(
    payload: StudentReservationCreateRequest,
    current_student: User = Depends(get_current_student),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    reservation = reservation_service.create_student_reservation(current_student, payload)
    return {
        "success": True,
        "message": "Reservation created successfully.",
        "data": build_reservation_write_data(reservation).model_dump(),
    }


@router.get("/reservations/current")
def list_student_current_reservations(
    current_student: User = Depends(get_current_student),
    history_service: HistoryService = Depends(get_history_service),
):
    return history_service.list_student_current(current_student)


@router.get("/reservations/history")
def list_student_reservation_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_student: User = Depends(get_current_student),
    history_service: HistoryService = Depends(get_history_service),
):
    return history_service.list_student_history(current_student, page=page, page_size=page_size)


@router.get("/rooms/{room_id}/seat-availability")
def list_student_room_seat_availability(
    room_id: int,
    params: SeatAvailabilityQueryParams = Depends(),
    current_student: User = Depends(get_current_student),
    availability_service: AvailabilityService = Depends(get_availability_service),
):
    result = availability_service.list_student_room_seat_availability(current_student, room_id, params)
    return {
        "items": [item.model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


@router.post("/reservations/{reservation_id}/cancel")
def cancel_student_reservation(
    reservation_id: int,
    payload: StudentReservationCancelRequest,
    current_student: User = Depends(get_current_student),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    reservation = reservation_service.cancel_student_reservation(current_student, reservation_id, payload)
    return {
        "success": True,
        "message": "Reservation cancelled successfully.",
        "data": build_reservation_write_data(reservation).model_dump(),
    }
