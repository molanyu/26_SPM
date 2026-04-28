from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.modules.reservation.services.checkin_access_service import CheckinReservationService
from app.modules.system_config.services.config_reader import ConfigReader
from app.modules.violation.services.checkin_violation_service import CheckinViolationService


@dataclass(slots=True)
class TimeoutReleaseResult:
    expired_reservation_ids: list[int]


class TimeoutService:
    def __init__(
        self,
        session: Session,
        violation_service: CheckinViolationService | None = None,
    ) -> None:
        self.session = session
        self.config_reader = ConfigReader(session)
        self.reservation_service = CheckinReservationService(session)
        self.violation_service = violation_service or CheckinViolationService(session)

    def release_overdue_reservations(self, *, now: datetime | None = None) -> TimeoutReleaseResult:
        now = now or datetime.now()
        violation_threshold_minutes = self.config_reader.get_violation_threshold_minutes()
        cutoff_time = now - timedelta(minutes=violation_threshold_minutes)
        expired_reservation_ids: list[int] = []
        for reservation in self.reservation_service.list_expirable_reservations(cutoff_time):
            if not self.reservation_service.mark_expired(reservation.reservation_id):
                continue
            self.violation_service.record_missed_checkin(
                reservation_id=reservation.reservation_id,
                user_id=reservation.user_id,
                occurred_at=now,
            )
            expired_reservation_ids.append(reservation.reservation_id)
        self.session.commit()
        return TimeoutReleaseResult(expired_reservation_ids=expired_reservation_ids)
