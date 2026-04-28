from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, BadRequestError, NotFoundError
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.resource.services.visibility_service import VisibilityService


@dataclass(slots=True)
class ReservableSeatSnapshot:
    seat_id: int
    room_id: int
    room_department_id: int | None
    is_department_only: bool
    open_time: time
    close_time: time


class ReservationAccessService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.visibility_service = VisibilityService(session)

    def get_reservable_seat_snapshot(
        self,
        seat_id: int,
        *,
        user_department_id: int | None,
    ) -> ReservableSeatSnapshot:
        statement = (
            select(
                Seat.id,
                Seat.room_id,
                Seat.is_active,
                StudyRoom.is_active,
                StudyRoom.department_id,
                StudyRoom.is_department_only,
                StudyRoom.open_time,
                StudyRoom.close_time,
            )
            .join(StudyRoom, StudyRoom.id == Seat.room_id)
            .where(Seat.id == seat_id)
        )
        row = self.session.execute(statement).one_or_none()
        if row is None:
            raise NotFoundError("Seat does not exist.")

        seat_active = row[2]
        room_active = row[3]
        room_department_id = row[4]
        is_department_only = row[5]
        if not room_active:
            raise BadRequestError("Study room is not available for reservation.")
        if not seat_active:
            raise BadRequestError("Seat is not available for reservation.")
        if not self.visibility_service.can_student_access_room_scope(
            user_department_id,
            room_department_id,
            is_department_only,
            is_active=room_active,
        ):
            raise AuthorizationError("The current user cannot reserve this seat.")

        return ReservableSeatSnapshot(
            seat_id=row[0],
            room_id=row[1],
            room_department_id=room_department_id,
            is_department_only=is_department_only,
            open_time=row[6],
            close_time=row[7],
        )
