from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.modules.identity.models.user import User
from app.modules.identity.services.department_service import DepartmentService
from app.modules.resource.models.study_room import StudyRoom
from app.modules.resource.repositories.room_repository import RoomRepository
from app.modules.resource.schemas.room import AdminRoomRead, RoomCreateRequest, RoomUpdateRequest, StudentRoomRead
from app.modules.resource.services.visibility_service import VisibilityService


class RoomService:
    def __init__(self, session: Session) -> None:
        self.room_repository = RoomRepository(session)
        self.visibility_service = VisibilityService(session)
        self.department_service = DepartmentService(session)

    def list_student_rooms(
        self,
        current_student: User,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, int | list[dict[str, object]]]:
        if page < 1 or page_size < 1:
            raise BadRequestError("page and page_size must be positive integers.")
        rooms = self.room_repository.list_student_visible_rooms(
            current_student.department_id,
            page=page,
            page_size=page_size,
        )
        total = self.room_repository.count_student_visible_rooms(current_student.department_id)
        items = [self._build_student_room(room).model_dump() for room in rooms]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_student_visible_room(self, current_student: User, room_id: int) -> StudyRoom:
        room = self.room_repository.get_student_visible_room_by_id(room_id, current_student.department_id)
        if room is None:
            raise NotFoundError("自习室不存在。")
        return room

    def list_admin_rooms(self) -> dict[str, int | list[dict[str, object]]]:
        rooms = self.room_repository.list_admin_rooms()
        items = [AdminRoomRead.model_validate(room).model_dump() for room in rooms]
        return {
            "items": items,
            "total": len(items),
            "page": 1,
            "page_size": len(items),
        }

    def create_room(self, payload: RoomCreateRequest) -> StudyRoom:
        department_id = self._resolve_department_id(payload)
        room = StudyRoom(
            name=payload.name,
            location=payload.location,
            department_id=department_id,
            is_department_only=payload.is_department_only,
            is_active=payload.is_active,
            open_time=payload.open_time,
            close_time=payload.close_time,
        )
        return self.room_repository.create(room)

    def update_room(self, room_id: int, payload: RoomUpdateRequest) -> StudyRoom:
        room = self.room_repository.get_by_id(room_id)
        if room is None:
            raise NotFoundError("自习室不存在。")
        department_id = self._resolve_department_id(payload)
        room.name = payload.name
        room.location = payload.location
        room.department_id = department_id
        room.is_department_only = payload.is_department_only
        room.is_active = payload.is_active
        room.open_time = payload.open_time
        room.close_time = payload.close_time
        return self.room_repository.save(room)

    def deactivate_room(self, room_id: int) -> StudyRoom:
        room = self.room_repository.get_by_id(room_id)
        if room is None:
            raise NotFoundError("自习室不存在。")
        room.is_active = False
        return self.room_repository.save(room)

    def _build_student_room(self, room: StudyRoom) -> StudentRoomRead:
        return StudentRoomRead(
            id=room.id,
            name=room.name,
            location=room.location,
            open_time=room.open_time,
            close_time=room.close_time,
            department_scope=self.visibility_service.build_department_scope(room),
        )

    def _resolve_department_id(self, payload: RoomCreateRequest | RoomUpdateRequest) -> int | None:
        if payload.department_id is not None:
            department = self.department_service.get_active_department(payload.department_id)
            if department is None:
                raise BadRequestError(
                    "所选院系不存在或已停用，请重新选择。",
                    details={"field": "department_id", "value": payload.department_id},
                )
        if not payload.is_department_only:
            return None
        return payload.department_id
