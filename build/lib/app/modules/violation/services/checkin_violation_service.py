from __future__ import annotations

from datetime import datetime
from typing import final

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.violation.services.violation_service import ViolationService


@final
class CheckinViolationService:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def record_timeout_violation(
        self,
        reservation_id: int,
        *,
        occurred_at: datetime | None = None,
        remark: str | None = None,
    ) -> None:
        if self._session is not None:
            ViolationService(self._session).record_timeout_violation(
                reservation_id,
                occurred_at=occurred_at,
                remark=remark,
            )
            return

        with SessionLocal() as session:
            ViolationService(session).record_timeout_violation(
                reservation_id,
                occurred_at=occurred_at,
                remark=remark,
            )
            session.commit()

    def record_missed_checkin(
        self,
        *,
        reservation_id: int,
        user_id: int,
        occurred_at: datetime,
    ) -> None:
        _ = user_id
        self.record_timeout_violation(reservation_id, occurred_at=occurred_at)
