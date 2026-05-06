from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.modules.checkin.models.checkin_record import CheckinRecord
from app.modules.checkin.services.code_service import CodeService, DynamicCheckinCode
from app.modules.identity.models.user import User
from app.modules.resource.services.checkin_room_service import CheckinRoomService


@dataclass(slots=True)
class AdminCheckinRecordList:
    items: list[dict[str, object]]
    total: int
    page: int
    page_size: int


class AdminCheckinService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or load_settings()
        self.code_service = CodeService(session, settings=self.settings)
        self.room_service = CheckinRoomService(session)

    def list_active_rooms(self) -> list[dict[str, object]]:
        return [
            {
                "id": room.room_id,
                "name": room.name,
            }
            for room in self.room_service.list_active_room_snapshots()
        ]

    def get_current_dynamic_code(
        self,
        room_id: int,
        *,
        now: datetime | None = None,
    ) -> DynamicCheckinCode:
        return self.code_service.get_current_dynamic_code(room_id, now=now)

    def list_records(
        self,
        *,
        room_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminCheckinRecordList:
        statement = select(CheckinRecord, User.student_no).join(User, User.id == CheckinRecord.user_id)
        if room_id is not None:
            statement = statement.where(CheckinRecord.room_id == room_id)
        if date_from is not None:
            statement = statement.where(CheckinRecord.checkin_at >= datetime.combine(date_from, time.min))
        if date_to is not None:
            statement = statement.where(
                CheckinRecord.checkin_at < datetime.combine(date_to + timedelta(days=1), time.min),
            )

        total_statement = statement.with_only_columns(func.count(CheckinRecord.id)).order_by(None)
        total = int(self.session.scalar(total_statement) or 0)
        rows = self.session.execute(
            statement.order_by(CheckinRecord.checkin_at.desc(), CheckinRecord.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size),
        ).all()
        items = [
            {
                "checkin_record_id": record.id,
                "reservation_id": record.reservation_id,
                "user_id": record.user_id,
                "student_no": student_no,
                "room_id": record.room_id,
                "seat_id": record.seat_id,
                "checkin_method": record.checkin_method,
                "checkin_at": record.checkin_at,
                "is_valid": record.is_valid,
            }
            for record, student_no in rows
        ]
        return AdminCheckinRecordList(items=items, total=total, page=page, page_size=page_size)
