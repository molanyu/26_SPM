from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.core.errors import BadRequestError
from app.modules.notification.models.notification_log import (
    NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE,
    NOTIFICATION_TYPE_NO_SHOW_REMINDER,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
    NotificationLog,
)
from app.modules.notification.services.reminder_service import ReminderService

SUPPORTED_TASK_TYPES = {
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
    NOTIFICATION_TYPE_NO_SHOW_REMINDER,
    NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE,
}


@dataclass(slots=True)
class AdminNotificationLogList:
    items: list[dict[str, object]]
    total: int
    page: int
    page_size: int


@dataclass(slots=True)
class AdminNotificationTaskResult:
    notification_type: str
    sent_reservation_ids: list[int]
    triggered_at: datetime


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

    def trigger_task(self, notification_type: str, *, now: datetime | None = None) -> AdminNotificationTaskResult:
        if notification_type not in SUPPORTED_TASK_TYPES:
            raise BadRequestError("不支持的通知任务类型。")
        triggered_at = (now or datetime.now()).replace(second=0, microsecond=0)
        reminder_service = ReminderService(self.session, settings=self.settings)
        if notification_type == NOTIFICATION_TYPE_RESERVATION_REMINDER:
            result = reminder_service.send_reservation_reminders(now=triggered_at)
        elif notification_type == NOTIFICATION_TYPE_NO_SHOW_REMINDER:
            result = reminder_service.send_no_show_reminders(now=triggered_at)
        else:
            result = reminder_service.send_auto_cancel_notifications(now=triggered_at)
        return AdminNotificationTaskResult(
            notification_type=notification_type,
            sent_reservation_ids=result.sent_reservation_ids,
            triggered_at=triggered_at,
        )
