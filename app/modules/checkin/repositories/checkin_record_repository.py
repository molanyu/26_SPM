from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.checkin.models.checkin_record import CheckinRecord


class CheckinRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_valid_by_reservation_id(self, reservation_id: int) -> CheckinRecord | None:
        statement = select(CheckinRecord).where(
            CheckinRecord.reservation_id == reservation_id,
            CheckinRecord.is_valid.is_(True),
        )
        return self.session.scalar(statement)

    def add(self, record: CheckinRecord) -> None:
        self.session.add(record)
