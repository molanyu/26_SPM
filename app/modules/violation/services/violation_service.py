from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.modules.reservation.models.reservation import (
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.system_config.services.config_reader import ConfigReader
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)
from app.modules.violation.repositories.violation_repository import ViolationRepository
from app.modules.violation.schemas.violation import UserPenaltyStatusRead


class ViolationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ViolationRepository(session)
        self.config_reader = ConfigReader(session)

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

    def get_user_penalty_status(
        self,
        user_id: int,
        as_of: datetime | None = None,
    ) -> UserPenaltyStatusRead:
        effective_as_of = as_of or datetime.now()
        threshold_count = self.config_reader.get_violation_penalty_threshold_count()
        window_days = self.config_reader.get_violation_penalty_window_days()
        duration_days = self.config_reader.get_violation_penalty_duration_days()

        window_start = effective_as_of - timedelta(days=window_days)
        violation_count = self.repository.count_unique_no_show_violations(
            user_id=user_id,
            window_start=window_start,
            window_end=effective_as_of,
        )

        penalty_start = None
        penalty_end = None
        is_penalized = False
        if violation_count >= threshold_count:
            threshold_times = self.repository.list_unique_no_show_occurred_at_for_penalty(
                user_id=user_id,
                window_start=window_start,
                window_end=effective_as_of,
                limit=threshold_count,
            )
            if len(threshold_times) >= threshold_count:
                penalty_start = threshold_times[threshold_count - 1]
                penalty_end = penalty_start + timedelta(days=duration_days)
                is_penalized = penalty_end > effective_as_of

        return UserPenaltyStatusRead(
            is_penalized=is_penalized,
            violation_count=violation_count,
            window_start=window_start,
            window_end=effective_as_of,
            penalty_start=penalty_start,
            penalty_end=penalty_end,
        )
