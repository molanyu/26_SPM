from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.notification.models.notification_log import NotificationLog


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_log(self, reservation_id: int, notification_type: str) -> NotificationLog | None:
        statement = select(NotificationLog).where(
            NotificationLog.reservation_id == reservation_id,
            NotificationLog.notification_type == notification_type,
        )
        return self.session.scalar(statement)

    def get_by_id(self, notification_log_id: int) -> NotificationLog | None:
        return self.session.get(NotificationLog, notification_log_id)

    def add(self, notification_log: NotificationLog) -> NotificationLog:
        self.session.add(notification_log)
        self.session.flush()
        return notification_log

    def claim_failed_log(
        self,
        notification_log_id: int,
        *,
        message: str,
        channel: str,
        sent_at: datetime,
        from_status: str,
        to_status: str,
    ) -> NotificationLog | None:
        statement = (
            update(NotificationLog)
            .where(
                NotificationLog.id == notification_log_id,
                NotificationLog.status == from_status,
            )
            .values(
                status=to_status,
                message=message,
                channel=channel,
                sent_at=sent_at,
            )
        )
        result = self.session.execute(statement)
        if result.rowcount != 1:
            return None
        self.session.flush()
        return self.get_by_id(notification_log_id)

    def transition_status(
        self,
        notification_log_id: int,
        *,
        from_status: str,
        to_status: str,
        message: str,
        channel: str,
        sent_at: datetime,
    ) -> NotificationLog | None:
        statement = (
            update(NotificationLog)
            .where(
                NotificationLog.id == notification_log_id,
                NotificationLog.status == from_status,
            )
            .values(
                status=to_status,
                message=message,
                channel=channel,
                sent_at=sent_at,
            )
        )
        result = self.session.execute(statement)
        if result.rowcount != 1:
            return None
        self.session.flush()
        return self.get_by_id(notification_log_id)
