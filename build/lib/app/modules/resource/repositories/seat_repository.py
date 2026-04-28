from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.resource.models.seat import Seat


class SeatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_student_visible_seats(
        self,
        room_id: int,
        *,
        is_window_side: bool | None = None,
        has_power_socket: bool | None = None,
        has_track_socket: bool | None = None,
    ) -> list[Seat]:
        statement = (
            select(Seat)
            .where(
                Seat.room_id == room_id,
                Seat.is_active.is_(True),
            )
            .order_by(Seat.id.asc())
        )
        if is_window_side is not None:
            statement = statement.where(Seat.is_window_side.is_(is_window_side))
        if has_power_socket is not None:
            statement = statement.where(Seat.has_power_socket.is_(has_power_socket))
        if has_track_socket is not None:
            statement = statement.where(Seat.has_track_socket.is_(has_track_socket))
        return list(self.session.scalars(statement))

    def list_admin_seats(self, room_id: int | None = None) -> list[Seat]:
        statement = select(Seat).order_by(Seat.id.asc())
        if room_id is not None:
            statement = statement.where(Seat.room_id == room_id)
        return list(self.session.scalars(statement))

    def get_by_id(self, seat_id: int) -> Seat | None:
        return self.session.get(Seat, seat_id)

    def get_by_room_and_code(
        self,
        room_id: int,
        seat_code: str,
        *,
        exclude_seat_id: int | None = None,
    ) -> Seat | None:
        statement = select(Seat).where(Seat.room_id == room_id, Seat.seat_code == seat_code)
        if exclude_seat_id is not None:
            statement = statement.where(Seat.id != exclude_seat_id)
        return self.session.scalar(statement)

    def create(self, seat: Seat) -> Seat:
        self.session.add(seat)
        self.session.commit()
        self.session.refresh(seat)
        return seat

    def save(self, seat: Seat) -> Seat:
        self.session.add(seat)
        self.session.commit()
        self.session.refresh(seat)
        return seat
