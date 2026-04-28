from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.identity.models.user import User
from app.modules.resource.models.seat import Seat
from app.modules.resource.repositories.room_repository import RoomRepository
from app.modules.resource.repositories.seat_repository import SeatRepository
from app.modules.resource.schemas.seat import AdminSeatRead, SeatCreateRequest, SeatFilterParams, SeatUpdateRequest, StudentSeatRead
from app.modules.resource.services.visibility_service import VisibilityService


class SeatService:
    def __init__(self, session: Session) -> None:
        self.room_repository = RoomRepository(session)
        self.seat_repository = SeatRepository(session)
        self.visibility_service = VisibilityService(session)

    def list_student_seats(self, current_student: User, room_id: int, filters: SeatFilterParams):
        room = self.room_repository.get_student_visible_room_by_id(room_id, current_student.department_id)
        if room is None:
            raise NotFoundError("自习室不存在。")
        seats = self.seat_repository.list_student_visible_seats(
            room.id,
            is_window_side=filters.is_window_side,
            has_power_socket=filters.has_power_socket,
            has_track_socket=filters.has_track_socket,
        )
        items = [
            StudentSeatRead(
                seat_id=seat.id,
                seat_code=seat.seat_code,
                seat_label=seat.seat_label,
                status=self.visibility_service.build_student_seat_status(seat),
                is_window_side=seat.is_window_side,
                has_power_socket=seat.has_power_socket,
                has_track_socket=seat.has_track_socket,
            ).model_dump()
            for seat in seats
        ]
        return {
            "items": items,
            "total": len(items),
            "page": 1,
            "page_size": len(items),
        }

    def list_admin_seats(self, room_id: int | None = None):
        seats = self.seat_repository.list_admin_seats(room_id)
        items = [AdminSeatRead.model_validate(seat).model_dump() for seat in seats]
        return {
            "items": items,
            "total": len(items),
            "page": 1,
            "page_size": len(items),
        }

    def create_seat(self, payload: SeatCreateRequest) -> Seat:
        room = self.room_repository.get_by_id(payload.room_id)
        if room is None:
            raise NotFoundError("自习室不存在。")
        if self.seat_repository.get_by_room_and_code(payload.room_id, payload.seat_code):
            raise ConflictError("同一自习室内的座位编号不能重复。")
        seat = Seat(
            room_id=payload.room_id,
            seat_code=payload.seat_code,
            seat_label=payload.seat_label,
            is_active=payload.is_active,
            is_window_side=payload.is_window_side,
            has_power_socket=payload.has_power_socket,
            has_track_socket=payload.has_track_socket,
        )
        return self.seat_repository.create(seat)

    def update_seat(self, seat_id: int, payload: SeatUpdateRequest) -> Seat:
        seat = self.seat_repository.get_by_id(seat_id)
        if seat is None:
            raise NotFoundError("座位不存在。")
        room = self.room_repository.get_by_id(payload.room_id)
        if room is None:
            raise NotFoundError("自习室不存在。")
        duplicate = self.seat_repository.get_by_room_and_code(
            payload.room_id,
            payload.seat_code,
            exclude_seat_id=seat_id,
        )
        if duplicate is not None:
            raise ConflictError("同一自习室内的座位编号不能重复。")
        seat.room_id = payload.room_id
        seat.seat_code = payload.seat_code
        seat.seat_label = payload.seat_label
        seat.is_active = payload.is_active
        seat.is_window_side = payload.is_window_side
        seat.has_power_socket = payload.has_power_socket
        seat.has_track_socket = payload.has_track_socket
        return self.seat_repository.save(seat)

    def deactivate_seat(self, seat_id: int) -> Seat:
        seat = self.seat_repository.get_by_id(seat_id)
        if seat is None:
            raise NotFoundError("座位不存在。")
        seat.is_active = False
        return self.seat_repository.save(seat)
