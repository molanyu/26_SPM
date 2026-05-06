from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.identity.models.user import User
from app.modules.reservation.models.reservation import Reservation
from app.modules.violation.models.violation_record import ViolationRecord
from app.modules.violation.schemas.violation import ViolationQueryFilters


class ViolationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_reservation_and_type(self, reservation_id: int, violation_type: str) -> ViolationRecord | None:
        statement = select(ViolationRecord).where(
            ViolationRecord.reservation_id == reservation_id,
            ViolationRecord.violation_type == violation_type,
        )
        return self.session.scalar(statement)

    def add(self, violation_record: ViolationRecord) -> ViolationRecord:
        self.session.add(violation_record)
        self.session.flush()
        return violation_record

    def list_records(self, filters: ViolationQueryFilters) -> list[tuple[ViolationRecord, int, str | None]]:
        statement = self._build_query(filters)
        paged_statement = (
            statement.order_by(ViolationRecord.occurred_at.desc(), ViolationRecord.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        return list(self.session.execute(paged_statement).all())

    def count_records(self, filters: ViolationQueryFilters) -> int:
        statement = self._build_query(filters).with_only_columns(func.count(ViolationRecord.id)).order_by(None)
        return int(self.session.scalar(statement) or 0)

    def _build_query(self, filters: ViolationQueryFilters):
        statement = (
            select(ViolationRecord, Reservation.room_id, User.student_no)
            .join(
                Reservation,
                Reservation.id == ViolationRecord.reservation_id,
            )
            .join(User, User.id == ViolationRecord.user_id)
        )
        if filters.user_id is not None:
            statement = statement.where(ViolationRecord.user_id == filters.user_id)
        if filters.student_no is not None:
            statement = statement.where(User.student_no == filters.student_no)
        if filters.room_id is not None:
            statement = statement.where(Reservation.room_id == filters.room_id)
        if filters.date_from is not None:
            statement = statement.where(
                ViolationRecord.occurred_at >= datetime.combine(filters.date_from, time.min),
            )
        if filters.date_to is not None:
            statement = statement.where(
                ViolationRecord.occurred_at < datetime.combine(filters.date_to + timedelta(days=1), time.min),
            )
        return statement
