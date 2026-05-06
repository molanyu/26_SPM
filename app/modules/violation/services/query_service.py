from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.violation.repositories.violation_repository import ViolationRepository
from app.modules.violation.schemas.violation import ViolationQueryFilters, ViolationRecordRead


@dataclass(slots=True)
class ViolationListResult:
    items: list[ViolationRecordRead]
    total: int
    page: int
    page_size: int


class QueryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ViolationRepository(session)

    def list_records(self, filters: ViolationQueryFilters) -> ViolationListResult:
        rows = self.repository.list_records(filters)
        total = self.repository.count_records(filters)
        items = [
            ViolationRecordRead(
                violation_id=record.id,
                user_id=record.user_id,
                student_no=student_no,
                reservation_id=record.reservation_id,
                room_id=room_id,
                violation_type=record.violation_type,
                occurred_at=record.occurred_at,
                remark=record.remark,
                created_at=record.created_at,
            )
            for record, room_id, student_no in rows
        ]
        return ViolationListResult(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )
