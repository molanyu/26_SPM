from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.identity.services.permission_service import PermissionService
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


class VisibilityService:
    def __init__(self, session: Session) -> None:
        self.permission_service = PermissionService(session)

    def build_department_scope(self, room: StudyRoom) -> str:
        if room.is_department_only and room.department_id is not None:
            return "DEPARTMENT"
        return "PUBLIC"

    def can_student_access_room_scope(
        self,
        student_department_id: int | None,
        room_department_id: int | None,
        is_department_only: bool,
        *,
        is_active: bool,
    ) -> bool:
        if not is_active:
            return False
        return self.permission_service.can_access_department(
            student_department_id,
            room_department_id,
            is_department_only,
        )

    def can_student_access_room(self, student_department_id: int | None, room: StudyRoom) -> bool:
        return self.can_student_access_room_scope(
            student_department_id,
            room.department_id,
            room.is_department_only,
            is_active=room.is_active,
        )

    def build_student_seat_status(self, seat: Seat) -> str:
        return "AVAILABLE"
