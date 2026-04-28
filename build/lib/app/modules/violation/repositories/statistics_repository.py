from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Integer, case, cast, distinct, func, select
from sqlalchemy.orm import Session

from app.modules.reservation.models.reservation import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)


@dataclass(slots=True)
class RoomOccupiedDuration:
    room_id: int
    occupied_seconds: int


@dataclass(slots=True)
class SeatOccupiedDuration:
    seat_id: int
    occupied_seconds: int


class StatisticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_room_occupied_durations(
        self,
        *,
        room_ids: list[int],
        seat_ids: list[int],
        window_start: datetime,
        window_end: datetime,
    ) -> list[RoomOccupiedDuration]:
        if not room_ids or not seat_ids:
            return []
        overlap_seconds = self._build_overlap_seconds_expression(window_start=window_start, window_end=window_end)
        statement = (
            select(
                Reservation.room_id,
                func.coalesce(func.sum(overlap_seconds), 0),
            )
            .where(
                Reservation.room_id.in_(room_ids),
                Reservation.seat_id.in_(seat_ids),
                Reservation.status != RESERVATION_STATUS_CANCELLED,
                Reservation.start_time < window_end,
                Reservation.end_time > window_start,
            )
            .group_by(Reservation.room_id)
            .order_by(Reservation.room_id.asc())
        )
        return [
            RoomOccupiedDuration(
                room_id=row[0],
                occupied_seconds=int(row[1] or 0),
            )
            for row in self.session.execute(statement).all()
        ]

    def list_seat_occupied_durations(
        self,
        *,
        seat_ids: list[int],
        window_start: datetime,
        window_end: datetime,
    ) -> list[SeatOccupiedDuration]:
        if not seat_ids:
            return []
        overlap_seconds = self._build_overlap_seconds_expression(window_start=window_start, window_end=window_end)
        statement = (
            select(
                Reservation.seat_id,
                func.coalesce(func.sum(overlap_seconds), 0),
            )
            .where(
                Reservation.seat_id.in_(seat_ids),
                Reservation.status != RESERVATION_STATUS_CANCELLED,
                Reservation.start_time < window_end,
                Reservation.end_time > window_start,
            )
            .group_by(Reservation.seat_id)
            .order_by(Reservation.seat_id.asc())
        )
        return [
            SeatOccupiedDuration(
                seat_id=row[0],
                occupied_seconds=int(row[1] or 0),
            )
            for row in self.session.execute(statement).all()
        ]

    def count_violation_denominator(
        self,
        *,
        room_ids: list[int],
        seat_ids: list[int],
        window_start: datetime,
        window_end: datetime,
    ) -> int:
        if not room_ids or not seat_ids:
            return 0
        statement = select(func.count(Reservation.id)).where(
            Reservation.room_id.in_(room_ids),
            Reservation.seat_id.in_(seat_ids),
            Reservation.status.in_((RESERVATION_STATUS_CHECKED_IN, RESERVATION_STATUS_EXPIRED)),
            Reservation.start_time >= window_start,
            Reservation.start_time < window_end,
        )
        return int(self.session.scalar(statement) or 0)

    def count_no_show_violations(
        self,
        *,
        room_ids: list[int],
        seat_ids: list[int],
        window_start: datetime,
        window_end: datetime,
    ) -> int:
        if not room_ids or not seat_ids:
            return 0
        statement = (
            select(func.count(distinct(ViolationRecord.reservation_id)))
            .select_from(ViolationRecord)
            .join(Reservation, Reservation.id == ViolationRecord.reservation_id)
            .where(
                Reservation.room_id.in_(room_ids),
                Reservation.seat_id.in_(seat_ids),
                Reservation.start_time >= window_start,
                Reservation.start_time < window_end,
                ViolationRecord.violation_type == VIOLATION_TYPE_NO_SHOW_TIMEOUT,
            )
        )
        return int(self.session.scalar(statement) or 0)

    def _build_overlap_seconds_expression(self, *, window_start: datetime, window_end: datetime):
        clipped_start = case(
            (Reservation.start_time > window_start, Reservation.start_time),
            else_=window_start,
        )
        clipped_end = case(
            (Reservation.end_time < window_end, Reservation.end_time),
            else_=window_end,
        )
        return cast(func.extract("epoch", clipped_end), Integer) - cast(
            func.extract("epoch", clipped_start),
            Integer,
        )
