from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.modules.reservation.models.reservation import (
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)
from app.modules.violation.repositories.violation_repository import ViolationRepository


class ViolationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ViolationRepository(session)

    def record_timeout_violation(
        self,
        reservation_id: int,
        *,
        occurred_at: datetime | None = None,
        remark: str | None = None,
    ) -> ViolationRecord | None:
        reservation = self.session.get(Reservation, reservation_id)
        if reservation is None:
            raise NotFoundError("Reservation does not exist.")

        existing = self.repository.get_by_reservation_and_type(reservation_id, VIOLATION_TYPE_NO_SHOW_TIMEOUT)
        if existing is not None:
            return existing

        if reservation.status != RESERVATION_STATUS_EXPIRED:
            return None

        violation_record = ViolationRecord(
            user_id=reservation.user_id,
            reservation_id=reservation.id,
            violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
            occurred_at=occurred_at or datetime.now(),
            remark=remark,
        )

        try:
            with self.session.begin_nested():
                self.repository.add(violation_record)
        except IntegrityError:
            existing = self.repository.get_by_reservation_and_type(
                reservation_id,
                VIOLATION_TYPE_NO_SHOW_TIMEOUT,
            )
            if existing is None:
                raise
            return existing
        return violation_record
