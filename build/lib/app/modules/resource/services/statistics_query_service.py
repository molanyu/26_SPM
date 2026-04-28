from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


@dataclass(slots=True)
class RoomStatisticsContext:
    room_id: int
    room_name: str
    open_seconds_per_day: int
    active_seat_count: int


@dataclass(slots=True)
class SeatStatisticsContext:
    seat_id: int
    seat_code: str
    room_id: int
    open_seconds_per_day: int


@dataclass(slots=True)
class UsageStatisticsContext:
    rooms: list[RoomStatisticsContext]
    seats: list[SeatStatisticsContext]


class StatisticsQueryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_room_statistics_context(self) -> UsageStatisticsContext:
        room_statement = (
            select(
                StudyRoom.id,
                StudyRoom.name,
                StudyRoom.open_time,
                StudyRoom.close_time,
                func.count(Seat.id),
            )
            .select_from(StudyRoom)
            .outerjoin(
                Seat,
                and_(
                    Seat.room_id == StudyRoom.id,
                    Seat.is_active.is_(True),
                ),
            )
            .where(StudyRoom.is_active.is_(True))
            .group_by(
                StudyRoom.id,
                StudyRoom.name,
                StudyRoom.open_time,
                StudyRoom.close_time,
            )
            .order_by(StudyRoom.id.asc())
        )
        seat_statement = (
            select(
                Seat.id,
                Seat.seat_code,
                Seat.room_id,
                StudyRoom.open_time,
                StudyRoom.close_time,
            )
            .join(StudyRoom, StudyRoom.id == Seat.room_id)
            .where(
                StudyRoom.is_active.is_(True),
                Seat.is_active.is_(True),
            )
            .order_by(Seat.id.asc())
        )

        rooms = [
            RoomStatisticsContext(
                room_id=row[0],
                room_name=row[1],
                open_seconds_per_day=self._seconds_between(row[2], row[3]),
                active_seat_count=int(row[4] or 0),
            )
            for row in self.session.execute(room_statement).all()
        ]
        seats = [
            SeatStatisticsContext(
                seat_id=row[0],
                seat_code=row[1],
                room_id=row[2],
                open_seconds_per_day=self._seconds_between(row[3], row[4]),
            )
            for row in self.session.execute(seat_statement).all()
        ]
        return UsageStatisticsContext(rooms=rooms, seats=seats)

    def _seconds_between(self, start_time: time, end_time: time) -> int:
        anchor_day = date(2000, 1, 1)
        return int(
            (
                datetime.combine(anchor_day, end_time)
                - datetime.combine(anchor_day, start_time)
            ).total_seconds(),
        )
