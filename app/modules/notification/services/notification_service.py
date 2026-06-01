from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.modules.notification.models.notification_log import (
    NOTIFICATION_CHANNEL_MOCK,
    NOTIFICATION_CHANNEL_SMTP_EMAIL,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_PENDING,
    NOTIFICATION_STATUS_SENT,
    NotificationLog,
)
from app.modules.notification.repositories.notification_repository import NotificationRepository
from app.modules.notification.schemas.notification import NotificationRequest
from app.modules.identity.schemas.user import UserNotificationTarget
from app.modules.identity.services.user_service import UserService
from app.modules.notification.services.email_sender import SmtpEmailSender

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationSendResult:
    log: NotificationLog
    sent: bool


class NotificationService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        email_sender: SmtpEmailSender | None = None,
        user_service: UserService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or load_settings()
        self.repository = NotificationRepository(session)
        self.email_sender = email_sender or SmtpEmailSender(self.settings)
        self.user_service = user_service or UserService(session)

    def send_notification(
        self,
        notification_type: str,
        reservation_id: int,
        user_id: int,
        message: str,
        *,
        channel: str | None = None,
        sent_at: datetime | None = None,
    ) -> NotificationSendResult:
        sent_at = sent_at or datetime.now()
        resolved_channel = self._resolve_channel(channel)
        payload = NotificationRequest(
            notification_type=notification_type,
            reservation_id=reservation_id,
            user_id=user_id,
            message=message,
            channel=resolved_channel,
        )
        notification_log = self._claim_notification_log(
            notification_type=notification_type,
            reservation_id=reservation_id,
            user_id=user_id,
            message=message,
            channel=resolved_channel,
            sent_at=sent_at,
        )
        if notification_log is None:
            existing = self.repository.get_log(reservation_id, notification_type)
            if existing is None:
                raise RuntimeError("Notification log claim was lost before send.")
            return NotificationSendResult(log=existing, sent=False)

        try:
            self._deliver(payload, sent_at)
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
                channel=resolved_channel,
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
                channel=resolved_channel,
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

    def _deliver(self, payload: NotificationRequest, sent_at: datetime) -> None:
        if payload.channel == NOTIFICATION_CHANNEL_MOCK:
            self._mock_send(payload, sent_at)
            return

        recipient = self._get_notification_target(payload.user_id)
        self._smtp_send(payload, recipient, sent_at)

    def _mock_send(self, payload: NotificationRequest, sent_at: datetime) -> None:
        logger.info(
            "Mock notification sent: type=%s reservation_id=%s user_id=%s channel=%s sent_at=%s",
            payload.notification_type,
            payload.reservation_id,
            payload.user_id,
            payload.channel,
            sent_at.isoformat(),
        )

    def _smtp_send(
        self,
        payload: NotificationRequest,
        recipient: UserNotificationTarget,
        sent_at: datetime,
    ) -> None:
        if not recipient.is_active:
            raise ValueError("目标用户已停用，无法通过 smtp_email 通道发送通知。")
        if not self._is_usable_email(recipient.email):
            raise ValueError("目标用户缺少可用邮箱地址，无法通过 smtp_email 通道发送通知。")

        self.email_sender.send_email(
            to_email=str(recipient.email),
            subject=self._build_email_subject(payload.notification_type),
            body=payload.message,
        )
        logger.info(
            "SMTP notification sent: type=%s reservation_id=%s user_id=%s channel=%s sent_at=%s",
            payload.notification_type,
            payload.reservation_id,
            payload.user_id,
            payload.channel,
            sent_at.isoformat(),
        )

    def _get_notification_target(self, user_id: int) -> UserNotificationTarget:
        target = self.user_service.get_notification_target(user_id)
        if target is None:
            raise ValueError("目标用户不存在，无法发送通知。")
        return target

    def _resolve_channel(self, channel: str | None) -> str:
        raw_value = (channel or self.settings.notification_default_channel).strip().lower()
        if raw_value == "mock":
            return NOTIFICATION_CHANNEL_MOCK
        if raw_value == "smtp_email":
            return NOTIFICATION_CHANNEL_SMTP_EMAIL
        raise ValueError(f"不支持的通知通道配置：{channel or self.settings.notification_default_channel}")

    def _build_email_subject(self, notification_type: str) -> str:
        subjects = {
            "RESERVATION_REMINDER": "自习室预约即将开始提醒",
            "NO_SHOW_REMINDER": "自习室预约未签到提醒",
            "AUTO_CANCEL_NOTICE": "自习室预约过期释放通知",
        }
        return subjects.get(notification_type, "自习室预约通知")

    def _is_usable_email(self, value: str | None) -> bool:
        if value is None:
            return False
        email = value.strip()
        if not email or " " in email or email.count("@") != 1:
            return False
        local_part, domain_part = email.split("@", 1)
        return bool(local_part and domain_part)

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
