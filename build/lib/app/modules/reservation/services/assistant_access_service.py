from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.reservation.repositories.reservation_repository import ReservationRepository


@dataclass(slots=True)
class AssistantOccupiedSeatSnapshot:
    reservation_id: int
    room_id: int
    seat_id: int
    start_time: datetime
    end_time: datetime
    status: str


class AssistantReservationService:
    def __init__(self, session: Session) -> None:
        self.repository = ReservationRepository(session)

    def list_occupied_seat_snapshots(
        self,
        room_id: int,
        *,
        start_time: datetime,
        end_time: datetime,
    ) -> list[AssistantOccupiedSeatSnapshot]:
        return [
            AssistantOccupiedSeatSnapshot(
                reservation_id=row[0],
                room_id=row[1],
                seat_id=row[2],
                start_time=row[3],
                end_time=row[4],
                status=row[5],
            )
            for row in self.repository.list_room_occupied_seats(
                room_id,
                start_time=start_time,
                end_time=end_time,
            )
        ]
