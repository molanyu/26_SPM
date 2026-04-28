from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.dependencies import require_admin_permission
from app.modules.resource.schemas.room import RoomCreateRequest, RoomUpdateRequest
from app.modules.resource.schemas.seat import SeatCreateRequest, SeatUpdateRequest
from app.modules.resource.services.room_service import RoomService
from app.modules.resource.services.seat_service import SeatService

router = APIRouter(
    prefix="/admin",
    tags=["resource-admin"],
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)


def get_room_service(db: Session = Depends(get_db)) -> RoomService:
    return RoomService(db)


def get_seat_service(db: Session = Depends(get_db)) -> SeatService:
    return SeatService(db)


@router.get("/rooms")
def list_admin_rooms(room_service: RoomService = Depends(get_room_service)):
    return room_service.list_admin_rooms()


@router.post("/rooms")
def create_room(
    payload: RoomCreateRequest,
    room_service: RoomService = Depends(get_room_service),
):
    room = room_service.create_room(payload)
    return {
        "success": True,
        "message": "Study room created successfully.",
        "data": {
            "id": room.id,
            "name": room.name,
            "location": room.location,
            "department_id": room.department_id,
            "is_department_only": room.is_department_only,
            "is_active": room.is_active,
            "open_time": room.open_time,
            "close_time": room.close_time,
        },
    }


@router.put("/rooms/{room_id}")
def update_room(
    room_id: int,
    payload: RoomUpdateRequest,
    room_service: RoomService = Depends(get_room_service),
):
    room = room_service.update_room(room_id, payload)
    return {
        "success": True,
        "message": "Study room updated successfully.",
        "data": {
            "id": room.id,
            "name": room.name,
            "location": room.location,
            "department_id": room.department_id,
            "is_department_only": room.is_department_only,
            "is_active": room.is_active,
            "open_time": room.open_time,
            "close_time": room.close_time,
        },
    }


@router.post("/rooms/{room_id}/deactivate")
def deactivate_room(
    room_id: int,
    room_service: RoomService = Depends(get_room_service),
):
    room = room_service.deactivate_room(room_id)
    return {
        "success": True,
        "message": "Study room deactivated successfully.",
        "data": {
            "id": room.id,
            "name": room.name,
            "location": room.location,
            "department_id": room.department_id,
            "is_department_only": room.is_department_only,
            "is_active": room.is_active,
            "open_time": room.open_time,
            "close_time": room.close_time,
        },
    }


@router.get("/seats")
def list_admin_seats(
    room_id: int | None = Query(default=None),
    seat_service: SeatService = Depends(get_seat_service),
):
    return seat_service.list_admin_seats(room_id=room_id)


@router.post("/seats")
def create_seat(
    payload: SeatCreateRequest,
    seat_service: SeatService = Depends(get_seat_service),
):
    seat = seat_service.create_seat(payload)
    return {
        "success": True,
        "message": "Seat created successfully.",
        "data": {
            "id": seat.id,
            "room_id": seat.room_id,
            "seat_code": seat.seat_code,
            "seat_label": seat.seat_label,
            "is_active": seat.is_active,
            "is_window_side": seat.is_window_side,
            "has_power_socket": seat.has_power_socket,
            "has_track_socket": seat.has_track_socket,
        },
    }


@router.put("/seats/{seat_id}")
def update_seat(
    seat_id: int,
    payload: SeatUpdateRequest,
    seat_service: SeatService = Depends(get_seat_service),
):
    seat = seat_service.update_seat(seat_id, payload)
    return {
        "success": True,
        "message": "Seat updated successfully.",
        "data": {
            "id": seat.id,
            "room_id": seat.room_id,
            "seat_code": seat.seat_code,
            "seat_label": seat.seat_label,
            "is_active": seat.is_active,
            "is_window_side": seat.is_window_side,
            "has_power_socket": seat.has_power_socket,
            "has_track_socket": seat.has_track_socket,
        },
    }


@router.post("/seats/{seat_id}/deactivate")
def deactivate_seat(
    seat_id: int,
    seat_service: SeatService = Depends(get_seat_service),
):
    seat = seat_service.deactivate_seat(seat_id)
    return {
        "success": True,
        "message": "Seat deactivated successfully.",
        "data": {
            "id": seat.id,
            "room_id": seat.room_id,
            "seat_code": seat.seat_code,
            "seat_label": seat.seat_label,
            "is_active": seat.is_active,
            "is_window_side": seat.is_window_side,
            "has_power_socket": seat.has_power_socket,
            "has_track_socket": seat.has_track_socket,
        },
    }
