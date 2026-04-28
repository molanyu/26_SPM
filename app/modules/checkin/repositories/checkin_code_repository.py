from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.checkin.models.checkin_code import CheckinCode


class CheckinCodeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_room_and_date(self, room_id: int, code_date: date) -> CheckinCode | None:
        statement = select(CheckinCode).where(
            CheckinCode.room_id == room_id,
            CheckinCode.code_date == code_date,
        )
        return self.session.scalar(statement)

    def add(self, checkin_code: CheckinCode) -> None:
        self.session.add(checkin_code)
