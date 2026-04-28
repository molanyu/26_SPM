from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.reservation.models.reservation import (
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CHECKED_IN,
    Reservation,
)
from app.modules.reservation.schemas.reservation import AdminReservationQueryFilters
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


class ReservationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, reservation: Reservation) -> Reservation:
        self.session.add(reservation)
        self.session.commit()
        self.session.refresh(reservation)
        return reservation

    def save(self, reservation: Reservation) -> Reservation:
        self.session.add(reservation)
        self.session.commit()
        self.session.refresh(reservation)
        return reservation

    def get_by_id(self, reservation_id: int) -> Reservation | None:
        return self.session.get(Reservation, reservation_id)

    def get_checkin_projection(self, reservation_id: int):
        statement = select(
            Reservation.id,
            Reservation.user_id,
            Reservation.room_id,
            Reservation.seat_id,
            Reservation.start_time,
            Reservation.end_time,
            Reservation.status,
        ).where(Reservation.id == reservation_id)
        return self.session.execute(statement).one_or_none()

    def list_history(self, user_id: int, *, page: int, page_size: int) -> list[Reservation]:
        statement = (
            select(Reservation)
            .where(Reservation.user_id == user_id)
            .order_by(Reservation.start_time.desc(), Reservation.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement))

    def count_history(self, user_id: int) -> int:
        statement = select(func.count()).select_from(
            select(Reservation.id).where(Reservation.user_id == user_id).subquery(),
        )
        return int(self.session.scalar(statement) or 0)

    def list_current(
        self,
        user_id: int,
        *,
        current_time: datetime,
    ) -> list[Reservation]:
        statement = (
            select(Reservation)
            .where(
                Reservation.user_id == user_id,
                Reservation.status.in_((RESERVATION_STATUS_BOOKED, RESERVATION_STATUS_CHECKED_IN)),
                Reservation.end_time >= current_time,
            )
            .order_by(Reservation.start_time.asc(), Reservation.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_admin_records(self, filters: AdminReservationQueryFilters) -> list[Reservation]:
        statement = (
            self._build_admin_records_query(filters)
            .order_by(Reservation.start_time.desc(), Reservation.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        return list(self.session.scalars(statement))

    def count_admin_records(self, filters: AdminReservationQueryFilters) -> int:
        statement = self._build_admin_records_query(filters).with_only_columns(func.count(Reservation.id)).order_by(None)
        return int(self.session.scalar(statement) or 0)

    def list_booked_started_before(self, cutoff_time: datetime):
        statement = (
            select(
                Reservation.id,
                Reservation.user_id,
                Reservation.room_id,
                Reservation.seat_id,
                Reservation.start_time,
                Reservation.end_time,
                Reservation.status,
            )
            .where(
                Reservation.status == RESERVATION_STATUS_BOOKED,
                Reservation.start_time <= cutoff_time,
            )
            .order_by(Reservation.start_time.asc(), Reservation.id.asc())
        )
        return list(self.session.execute(statement).all())

    def list_booked_starting_between(self, window_start: datetime, window_end: datetime):
        statement = (
            select(
                Reservation.id,
                Reservation.user_id,
                Reservation.room_id,
                Reservation.seat_id,
                Reservation.start_time,
                Reservation.end_time,
                Reservation.status,
                StudyRoom.name,
                Seat.seat_code,
                Seat.seat_label,
            )
            .join(StudyRoom, StudyRoom.id == Reservation.room_id)
            .join(Seat, Seat.id == Reservation.seat_id)
            .where(
                Reservation.status == RESERVATION_STATUS_BOOKED,
                Reservation.start_time >= window_start,
                Reservation.start_time < window_end,
            )
            .order_by(Reservation.start_time.asc(), Reservation.id.asc())
        )
        return list(self.session.execute(statement).all())

    def list_expired_reservations(self):
        statement = (
            select(
                Reservation.id,
                Reservation.user_id,
                Reservation.room_id,
                Reservation.seat_id,
                Reservation.start_time,
                Reservation.end_time,
                Reservation.status,
                StudyRoom.name,
                Seat.seat_code,
                Seat.seat_label,
            )
            .join(StudyRoom, StudyRoom.id == Reservation.room_id)
            .join(Seat, Seat.id == Reservation.seat_id)
            .where(Reservation.status == "EXPIRED")
            .order_by(Reservation.updated_at.asc(), Reservation.id.asc())
        )
        return list(self.session.execute(statement).all())

    def get_conflicting_reservation(
        self,
        seat_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> Reservation | None:
        statement = (
            select(Reservation)
            .where(
                Reservation.seat_id == seat_id,
                Reservation.status == RESERVATION_STATUS_BOOKED,
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_room_occupied_seats(
        self,
        room_id: int,
        *,
        start_time: datetime,
        end_time: datetime,
    ):
        statement = (
            select(
                Reservation.id,
                Reservation.room_id,
                Reservation.seat_id,
                Reservation.start_time,
                Reservation.end_time,
                Reservation.status,
            )
            .where(
                Reservation.room_id == room_id,
                Reservation.status.in_((RESERVATION_STATUS_BOOKED, RESERVATION_STATUS_CHECKED_IN)),
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
            )
            .order_by(Reservation.start_time.asc(), Reservation.id.asc())
        )
        return list(self.session.execute(statement).all())

    def transition_status(
        self,
        reservation_id: int,
        *,
        current_status: str,
        new_status: str,
    ) -> bool:
        statement = (
            update(Reservation)
            .where(
                Reservation.id == reservation_id,
                Reservation.status == current_status,
            )
            .values(status=new_status)
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

    def _build_admin_records_query(self, filters: AdminReservationQueryFilters):
        statement = select(Reservation)
        if filters.user_id is not None:
            statement = statement.where(Reservation.user_id == filters.user_id)
        if filters.room_id is not None:
            statement = statement.where(Reservation.room_id == filters.room_id)
        if filters.seat_id is not None:
            statement = statement.where(Reservation.seat_id == filters.seat_id)
        if filters.status is not None:
            statement = statement.where(Reservation.status == filters.status)
        if filters.date_from is not None:
            statement = statement.where(
                Reservation.start_time >= datetime.combine(filters.date_from, time.min),
            )
        if filters.date_to is not None:
            statement = statement.where(
                Reservation.start_time < datetime.combine(filters.date_to + timedelta(days=1), time.min),
            )
        return statement
