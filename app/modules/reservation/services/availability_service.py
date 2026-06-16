from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError
from app.modules.identity.models.user import User
from app.modules.reservation.repositories.reservation_repository import ReservationRepository
from app.modules.reservation.schemas.reservation import SeatAvailabilityQueryParams, SeatAvailabilityRead
from app.modules.resource.schemas.seat import SeatFilterParams
from app.modules.resource.services.room_service import RoomService
from app.modules.resource.services.seat_service import SeatService


@dataclass(slots=True)
class SeatAvailabilityListResult:
    items: list[SeatAvailabilityRead]
    total: int
    page: int
    page_size: int


class AvailabilityService:
    def __init__(self, session: Session) -> None:
        self.repository = ReservationRepository(session)
        self.room_service = RoomService(session)
        self.seat_service = SeatService(session)

    def list_student_room_seat_availability(
        self,
        current_student: User,
        room_id: int,
        params: SeatAvailabilityQueryParams,
    ) -> SeatAvailabilityListResult:
        room = self.room_service.get_student_visible_room(current_student, room_id)
        if params.start_time < room.open_time or params.end_time > room.close_time:
            raise BadRequestError("Seat availability time must be within the study room open hours.")

        resource_seats = self.seat_service.list_student_seats(
            current_student,
            room_id,
            SeatFilterParams(
                date=params.date,
                start_time=params.start_time,
                end_time=params.end_time,
                is_window_side=params.is_window_side,
                has_power_socket=params.has_power_socket,
                has_track_socket=params.has_track_socket,
            ),
        )["items"]
        start_datetime = datetime.combine(params.date, params.start_time)
        end_datetime = datetime.combine(params.date, params.end_time)
        occupied_seat_ids = {
            row[2]
            for row in self.repository.list_room_occupied_seats(
                room_id,
                start_time=start_datetime,
                end_time=end_datetime,
            )
        }

        items = [
            SeatAvailabilityRead(
                seat_id=seat["seat_id"],
                seat_code=seat["seat_code"],
                seat_label=seat["seat_label"],
                status="OCCUPIED" if seat["seat_id"] in occupied_seat_ids else "AVAILABLE",
                is_window_side=seat["is_window_side"],
                has_power_socket=seat["has_power_socket"],
                has_track_socket=seat["has_track_socket"],
            )
            for seat in resource_seats
        ]
        return SeatAvailabilityListResult(
            items=items,
            total=len(items),
            page=1,
            page_size=len(items),
        )
