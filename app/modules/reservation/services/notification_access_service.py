from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.reservation.repositories.reservation_repository import ReservationRepository


@dataclass(slots=True)
class NotificationReservationSnapshot:
    reservation_id: int
    user_id: int
    room_id: int
    seat_id: int
    start_time: datetime
    end_time: datetime
    status: str
    room_name: str
    seat_code: str
    seat_label: str


@dataclass(slots=True)
class NotificationReservationService:
    session: Session
    repository: ReservationRepository = field(init=False)

    def __post_init__(self) -> None:
        self.repository = ReservationRepository(self.session)

    def list_reservation_reminder_candidates(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> list[NotificationReservationSnapshot]:
        return [
            self._build_snapshot(row)
            for row in self.repository.list_booked_starting_between(window_start, window_end)
        ]

    def list_no_show_reminder_candidates(
        self,
        cutoff_time: datetime,
    ) -> list[NotificationReservationSnapshot]:
        return [
            self._build_snapshot(row)
            for row in self.repository.list_booked_starting_on_or_before(cutoff_time)
        ]

    def list_auto_cancel_notice_candidates(self) -> list[NotificationReservationSnapshot]:
        return [
            self._build_snapshot(row)
            for row in self.repository.list_expired_reservations()
        ]

    def _build_snapshot(self, row) -> NotificationReservationSnapshot:
        return NotificationReservationSnapshot(
            reservation_id=row[0],
            user_id=row[1],
            room_id=row[2],
            seat_id=row[3],
            start_time=row[4],
            end_time=row[5],
            status=row[6],
            room_name=row[7],
            seat_code=row[8],
            seat_label=row[9],
        )
