from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.violation.repositories.violation_repository import ViolationRepository
from app.modules.violation.schemas.violation import (
    UserViolationSummaryRead,
    ViolationQueryFilters,
    ViolationRecordRead,
)
from app.modules.violation.services.violation_service import ViolationService


@dataclass(slots=True)
class ViolationListResult:
    items: list[ViolationRecordRead]
    total: int
    page: int
    page_size: int
    user_summary: UserViolationSummaryRead | None = None


class QueryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ViolationRepository(session)
        self.violation_service = ViolationService(session)

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
            user_summary=self._build_user_summary(filters),
        )

    def _build_user_summary(self, filters: ViolationQueryFilters) -> UserViolationSummaryRead | None:
        if filters.user_id is None and filters.student_no is None:
            return None
        resolved_user = self.repository.find_user_for_summary(
            user_id=filters.user_id,
            student_no=filters.student_no,
        )
        if resolved_user is None:
            return None
        user_id, _ = resolved_user
        return self.violation_service.get_user_violation_summary(user_id)
