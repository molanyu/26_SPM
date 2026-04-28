from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from threading import Lock
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.modules.reservation.repositories.reservation_repository import ReservationRepository

RESERVATION_CONFLICT_MESSAGE = "This seat is already reserved for the selected time range."
_seat_write_locks: dict[int, Lock] = {}
_seat_write_locks_guard = Lock()


class ConflictService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ReservationRepository(session)

    @contextmanager
    def serialized_seat_write(self, seat_id: int) -> Iterator[None]:
        with _seat_write_locks_guard:
            seat_lock = _seat_write_locks.setdefault(seat_id, Lock())
        with seat_lock:
            if self._is_postgresql_session():
                self.session.execute(
                    text("SELECT pg_advisory_xact_lock(:seat_id)"),
                    {"seat_id": seat_id},
                )
            yield

    def ensure_no_conflict(self, seat_id: int, start_time: datetime, end_time: datetime) -> None:
        if self.repository.get_conflicting_reservation(seat_id, start_time, end_time) is not None:
            raise ConflictError(RESERVATION_CONFLICT_MESSAGE)

    def _is_postgresql_session(self) -> bool:
        bind = self.session.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"
