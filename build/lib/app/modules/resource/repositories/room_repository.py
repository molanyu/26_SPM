from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.resource.models.study_room import StudyRoom


class RoomRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_student_visible_rooms(
        self,
        user_department_id: int | None,
        *,
        page: int,
        page_size: int,
    ) -> list[StudyRoom]:
        statement = (
            self._student_visibility_statement(user_department_id)
            .order_by(StudyRoom.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement))

    def count_student_visible_rooms(self, user_department_id: int | None) -> int:
        statement = select(func.count()).select_from(self._student_visibility_statement(user_department_id).subquery())
        return int(self.session.scalar(statement) or 0)

    def get_student_visible_room_by_id(
        self,
        room_id: int,
        user_department_id: int | None,
    ) -> StudyRoom | None:
        statement = self._student_visibility_statement(user_department_id).where(StudyRoom.id == room_id)
        return self.session.scalar(statement)

    def list_admin_rooms(self) -> list[StudyRoom]:
        statement = select(StudyRoom).order_by(StudyRoom.id.asc())
        return list(self.session.scalars(statement))

    def list_active_rooms(self) -> list[StudyRoom]:
        statement = select(StudyRoom).where(StudyRoom.is_active.is_(True)).order_by(StudyRoom.id.asc())
        return list(self.session.scalars(statement))

    def get_by_id(self, room_id: int) -> StudyRoom | None:
        return self.session.get(StudyRoom, room_id)

    def create(self, room: StudyRoom) -> StudyRoom:
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    def save(self, room: StudyRoom) -> StudyRoom:
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    def _student_visibility_statement(self, user_department_id: int | None):
        return select(StudyRoom).where(
            StudyRoom.is_active.is_(True),
            or_(
                StudyRoom.is_department_only.is_(False),
                StudyRoom.department_id.is_(None),
                StudyRoom.department_id == user_department_id,
            ),
        )
