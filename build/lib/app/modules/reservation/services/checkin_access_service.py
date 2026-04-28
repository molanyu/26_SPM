from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.modules.reservation.models.reservation import (
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CHECKED_IN,
    RESERVATION_STATUS_EXPIRED,
)
from app.modules.reservation.repositories.reservation_repository import ReservationRepository


@dataclass(slots=True)
class CheckinReservationSnapshot:
    reservation_id: int
    user_id: int
    room_id: int
    seat_id: int
    start_time: datetime
    end_time: datetime
    status: str


class CheckinReservationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ReservationRepository(session)

    def get_checkin_snapshot(self, reservation_id: int) -> CheckinReservationSnapshot:
        row = self.repository.get_checkin_projection(reservation_id)
        if row is None:
            raise NotFoundError("Reservation does not exist.")
        return CheckinReservationSnapshot(
            reservation_id=row[0],
            user_id=row[1],
            room_id=row[2],
            seat_id=row[3],
            start_time=row[4],
            end_time=row[5],
            status=row[6],
        )

    def list_expirable_reservations(self, cutoff_time: datetime) -> list[CheckinReservationSnapshot]:
        return [
            CheckinReservationSnapshot(
                reservation_id=row[0],
                user_id=row[1],
                room_id=row[2],
                seat_id=row[3],
                start_time=row[4],
                end_time=row[5],
                status=row[6],
            )
            for row in self.repository.list_booked_started_before(cutoff_time)
        ]

    def mark_checked_in(self, reservation_id: int) -> bool:
        return self.repository.transition_status(
            reservation_id,
            current_status=RESERVATION_STATUS_BOOKED,
            new_status=RESERVATION_STATUS_CHECKED_IN,
        )

    def mark_expired(self, reservation_id: int) -> bool:
        return self.repository.transition_status(
            reservation_id,
            current_status=RESERVATION_STATUS_BOOKED,
            new_status=RESERVATION_STATUS_EXPIRED,
        )
