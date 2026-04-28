from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.notification.models.notification_log import (
    NOTIFICATION_CHANNEL_MOCK,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_PENDING,
    NOTIFICATION_STATUS_SENT,
    NotificationLog,
)
from app.modules.notification.repositories.notification_repository import NotificationRepository
from app.modules.notification.schemas.notification import NotificationRequest

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationSendResult:
    log: NotificationLog
    sent: bool


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = NotificationRepository(session)

    def send_notification(
        self,
        notification_type: str,
        reservation_id: int,
        user_id: int,
        message: str,
        *,
        channel: str = NOTIFICATION_CHANNEL_MOCK,
        sent_at: datetime | None = None,
    ) -> NotificationSendResult:
        sent_at = sent_at or datetime.now()
        payload = NotificationRequest(
            notification_type=notification_type,
            reservation_id=reservation_id,
            user_id=user_id,
            message=message,
            channel=channel,
        )
        notification_log = self._claim_notification_log(
            notification_type=notification_type,
            reservation_id=reservation_id,
            user_id=user_id,
            message=message,
            channel=channel,
            sent_at=sent_at,
        )
        if notification_log is None:
            existing = self.repository.get_log(reservation_id, notification_type)
            if existing is None:
                raise RuntimeError("Notification log claim was lost before send.")
            return NotificationSendResult(log=existing, sent=False)

        try:
            self._mock_send(payload, sent_at)
        except Exception:
            logger.exception(
                "Notification send failed: type=%s reservation_id=%s user_id=%s",
                notification_type,
                reservation_id,
                user_id,
            )
            failed_log = self._transition_claimed_log(
                notification_log_id=notification_log.id,
                message=message,
                channel=channel,
                sent_at=sent_at,
                from_status=NOTIFICATION_STATUS_PENDING,
                to_status=NOTIFICATION_STATUS_FAILED,
            )
            if failed_log is None:
                current = self.repository.get_by_id(notification_log.id)
                if current is None:
                    raise RuntimeError("Notification log disappeared after failed send.")
                return NotificationSendResult(log=current, sent=False)
            return NotificationSendResult(log=failed_log, sent=False)

        try:
            sent_log = self._transition_claimed_log(
                notification_log_id=notification_log.id,
                message=message,
                channel=channel,
                sent_at=sent_at,
                from_status=NOTIFICATION_STATUS_PENDING,
                to_status=NOTIFICATION_STATUS_SENT,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Notification log {notification_log.id} could not be finalized after send."
            ) from exc
        if sent_log is None:
            current = self.repository.get_by_id(notification_log.id)
            if current is None:
                raise RuntimeError("Notification log disappeared after successful send.")
            raise RuntimeError(
                f"Notification log {notification_log.id} could not be finalized after send."
            )
        return NotificationSendResult(log=sent_log, sent=True)

    def _mock_send(self, payload: NotificationRequest, sent_at: datetime) -> None:
        logger.info(
            "Mock notification sent: type=%s reservation_id=%s user_id=%s channel=%s sent_at=%s",
            payload.notification_type,
            payload.reservation_id,
            payload.user_id,
            payload.channel,
            sent_at.isoformat(),
        )

    def _claim_notification_log(
        self,
        *,
        notification_type: str,
        reservation_id: int,
        user_id: int,
        message: str,
        channel: str,
        sent_at: datetime,
    ) -> NotificationLog | None:
        existing = self.repository.get_log(reservation_id, notification_type)
        if existing is not None:
            if existing.status in {NOTIFICATION_STATUS_SENT, NOTIFICATION_STATUS_PENDING}:
                return None
            if existing.status == NOTIFICATION_STATUS_FAILED:
                claimed_log = self.repository.claim_failed_log(
                    existing.id,
                    message=message,
                    channel=channel,
                    sent_at=sent_at,
                    from_status=NOTIFICATION_STATUS_FAILED,
                    to_status=NOTIFICATION_STATUS_PENDING,
                )
                if claimed_log is None:
                    self.session.rollback()
                    return None
                self.session.commit()
                return claimed_log

        notification_log = NotificationLog(
            user_id=user_id,
            reservation_id=reservation_id,
            notification_type=notification_type,
            channel=channel,
            status=NOTIFICATION_STATUS_PENDING,
            message=message,
            sent_at=sent_at,
        )
        try:
            self.repository.add(notification_log)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            return None
        return notification_log

    def _transition_claimed_log(
        self,
        *,
        notification_log_id: int,
        message: str,
        channel: str,
        sent_at: datetime,
        from_status: str,
        to_status: str,
    ) -> NotificationLog | None:
        try:
            notification_log = self.repository.transition_status(
                notification_log_id,
                from_status=from_status,
                to_status=to_status,
                message=message,
                channel=channel,
                sent_at=sent_at,
            )
            if notification_log is None:
                self.session.rollback()
                return None
            self.session.commit()
            return notification_log
        except Exception:
            self.session.rollback()
            raise
