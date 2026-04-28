from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_student
from app.modules.identity.models.user import User
from app.modules.resource.schemas.seat import SeatFilterParams
from app.modules.resource.services.room_service import RoomService
from app.modules.resource.services.seat_service import SeatService

router = APIRouter(prefix="/student", tags=["resource-student"])


def get_room_service(db: Session = Depends(get_db)) -> RoomService:
    return RoomService(db)


def get_seat_service(db: Session = Depends(get_db)) -> SeatService:
    return SeatService(db)


@router.get("/rooms")
def list_student_rooms(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_student: User = Depends(get_current_student),
    room_service: RoomService = Depends(get_room_service),
):
    return room_service.list_student_rooms(current_student, page=page, page_size=page_size)


@router.get("/rooms/{room_id}/seats")
def list_student_room_seats(
    room_id: int,
    filters: SeatFilterParams = Depends(),
    current_student: User = Depends(get_current_student),
    seat_service: SeatService = Depends(get_seat_service),
):
    return seat_service.list_student_seats(current_student, room_id, filters)
