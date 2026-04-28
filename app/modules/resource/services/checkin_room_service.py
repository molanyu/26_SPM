from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.modules.resource.repositories.room_repository import RoomRepository


@dataclass(slots=True)
class CheckinRoomSnapshot:
    room_id: int
    name: str
    is_active: bool


class CheckinRoomService:
    def __init__(self, session: Session) -> None:
        self.repository = RoomRepository(session)

    def get_room_snapshot(self, room_id: int) -> CheckinRoomSnapshot:
        room = self.repository.get_by_id(room_id)
        if room is None:
            raise NotFoundError("Study room does not exist.")
        return CheckinRoomSnapshot(room_id=room.id, name=room.name, is_active=room.is_active)

    def get_active_room_snapshot(self, room_id: int) -> CheckinRoomSnapshot:
        room = self.get_room_snapshot(room_id)
        if not room.is_active:
            raise BadRequestError("Study room is not available for check-in.")
        return room

    def list_active_room_snapshots(self) -> list[CheckinRoomSnapshot]:
        return [
            CheckinRoomSnapshot(room_id=room.id, name=room.name, is_active=room.is_active)
            for room in self.repository.list_active_rooms()
        ]
