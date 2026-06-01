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
USER_RESERVATION_OVERLAP_MESSAGE = "The user already has an active reservation for the selected time range."
_LOCK_ORDER = {"seat": 0, "user": 1}
_write_locks: dict[tuple[str, int], Lock] = {}
_write_locks_guard = Lock()


class ConflictService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ReservationRepository(session)

    @contextmanager
    def serialized_seat_write(self, seat_id: int) -> Iterator[None]:
        with self._serialized_write((("seat", seat_id),)):
            yield

    @contextmanager
    def serialized_reservation_write(self, *, user_id: int, seat_id: int) -> Iterator[None]:
        with self._serialized_write((("seat", seat_id), ("user", user_id))):
            yield

    def ensure_no_conflict(self, seat_id: int, start_time: datetime, end_time: datetime) -> None:
        if self.repository.get_conflicting_reservation(seat_id, start_time, end_time) is not None:
            raise ConflictError(RESERVATION_CONFLICT_MESSAGE)

    def ensure_user_has_no_overlap(self, user_id: int, start_time: datetime, end_time: datetime) -> None:
        if self.repository.get_conflicting_user_reservation(user_id, start_time, end_time) is not None:
            raise ConflictError(USER_RESERVATION_OVERLAP_MESSAGE)

    @contextmanager
    def _serialized_write(self, raw_lock_keys: tuple[tuple[str, int], ...]) -> Iterator[None]:
        lock_keys = tuple(
            sorted(
                set(raw_lock_keys),
                key=lambda item: (_LOCK_ORDER[item[0]], item[1]),
            )
        )
        with _write_locks_guard:
            locks = [_write_locks.setdefault(key, Lock()) for key in lock_keys]
        for lock in locks:
            lock.acquire()
        try:
            if self._is_postgresql_session():
                for kind, value in lock_keys:
                    self.session.execute(
                        text("SELECT pg_advisory_xact_lock(:namespace, :value)"),
                        {"namespace": _LOCK_ORDER[kind] + 1, "value": value},
                    )
            yield
        finally:
            for lock in reversed(locks):
                lock.release()

    def _is_postgresql_session(self) -> bool:
        bind = self.session.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"
