from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.modules.notification.models.notification_log import NotificationLog


@dataclass(slots=True)
class AdminNotificationLogList:
    items: list[dict[str, object]]
    total: int
    page: int
    page_size: int


class AdminNotificationService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or load_settings()

    def list_logs(
        self,
        *,
        reservation_id: int | None = None,
        notification_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminNotificationLogList:
        statement = select(NotificationLog)
        if reservation_id is not None:
            statement = statement.where(NotificationLog.reservation_id == reservation_id)
        if notification_type:
            statement = statement.where(NotificationLog.notification_type == notification_type)
        if status:
            statement = statement.where(NotificationLog.status == status)

        total_statement = statement.with_only_columns(func.count(NotificationLog.id)).order_by(None)
        total = int(self.session.scalar(total_statement) or 0)
        logs = self.session.execute(
            statement.order_by(NotificationLog.sent_at.desc(), NotificationLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size),
        ).scalars().all()
        items = [
            {
                "notification_log_id": log.id,
                "reservation_id": log.reservation_id,
                "user_id": log.user_id,
                "notification_type": log.notification_type,
                "channel": log.channel,
                "status": log.status,
                "message": log.message,
                "sent_at": log.sent_at,
            }
            for log in logs
        ]
        return AdminNotificationLogList(items=items, total=total, page=page, page_size=page_size)
