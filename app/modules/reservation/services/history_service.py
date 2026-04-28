from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError
from app.modules.identity.models.user import User
from app.modules.reservation.repositories.reservation_repository import ReservationRepository
from app.modules.reservation.services.reservation_service import build_reservation_write_data


class HistoryService:
    def __init__(self, session: Session) -> None:
        self.repository = ReservationRepository(session)

    def list_student_history(
        self,
        current_student: User,
        *,
        page: int = 1,
        page_size: int = 20,
    ):
        if page < 1 or page_size < 1:
            raise BadRequestError("page and page_size must be positive integers.")
        reservations = self.repository.list_history(current_student.id, page=page, page_size=page_size)
        total = self.repository.count_history(current_student.id)
        items = [
            build_reservation_write_data(reservation).model_dump()
            for reservation in reservations
        ]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_student_current(self, current_student: User):
        reservations = self.repository.list_current(
            current_student.id,
            current_time=datetime.now(),
        )
        items = [
            build_reservation_write_data(reservation).model_dump()
            for reservation in reservations
        ]
        return {
            "items": items,
            "total": len(items),
        }
