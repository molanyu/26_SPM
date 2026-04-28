from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.checkin.services.timeout_service import TimeoutService
from app.modules.violation.services.checkin_violation_service import CheckinViolationService


def release_expired_reservations(
    session: Session,
    *,
    now: datetime | None = None,
    violation_service: CheckinViolationService | None = None,
):
    violation_service = violation_service or CheckinViolationService(session)
    service = TimeoutService(session, violation_service=violation_service)
    return service.release_overdue_reservations(now=now)
