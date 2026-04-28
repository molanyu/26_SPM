from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.modules.notification.models.notification_log import (
    NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE,
    NOTIFICATION_TYPE_NO_SHOW_REMINDER,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
)
from app.modules.notification.services.email_sender import SmtpEmailSender
from app.modules.notification.services.notification_service import NotificationService
from app.modules.reservation.services.notification_access_service import (
    NotificationReservationService,
    NotificationReservationSnapshot,
)


@dataclass(slots=True)
class ReminderTaskResult:
    sent_reservation_ids: list[int]


class ReminderService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        email_sender: SmtpEmailSender | None = None,
    ) -> None:
        self.session = session
        resolved_settings = settings or load_settings()
        self.notification_service = NotificationService(
            session,
            settings=resolved_settings,
            email_sender=email_sender,
        )
        self.reservation_service = NotificationReservationService(session)

    def send_reservation_reminders(self, *, now: datetime | None = None) -> ReminderTaskResult:
        current_minute = self._normalize_now(now)
        window_start = current_minute + timedelta(minutes=15)
        window_end = window_start + timedelta(minutes=1)
        candidates = self.reservation_service.list_reservation_reminder_candidates(window_start, window_end)
        return self._send_candidates(
            candidates,
            notification_type=NOTIFICATION_TYPE_RESERVATION_REMINDER,
            sent_at=current_minute,
            message_builder=self._build_reservation_reminder_message,
        )

    def send_no_show_reminders(self, *, now: datetime | None = None) -> ReminderTaskResult:
        current_minute = self._normalize_now(now)
        window_start = current_minute - timedelta(minutes=10)
        window_end = window_start + timedelta(minutes=1)
        candidates = self.reservation_service.list_no_show_reminder_candidates(window_start, window_end)
        return self._send_candidates(
            candidates,
            notification_type=NOTIFICATION_TYPE_NO_SHOW_REMINDER,
            sent_at=current_minute,
            message_builder=self._build_no_show_reminder_message,
        )

    def send_auto_cancel_notifications(self, *, now: datetime | None = None) -> ReminderTaskResult:
        current_minute = self._normalize_now(now)
        candidates = self.reservation_service.list_auto_cancel_notice_candidates()
        return self._send_candidates(
            candidates,
            notification_type=NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE,
            sent_at=current_minute,
            message_builder=self._build_auto_cancel_message,
        )

    def _send_candidates(
        self,
        candidates: list[NotificationReservationSnapshot],
        *,
        notification_type: str,
        sent_at: datetime,
        message_builder,
    ) -> ReminderTaskResult:
        sent_reservation_ids: list[int] = []
        try:
            for candidate in candidates:
                result = self.notification_service.send_notification(
                    notification_type,
                    candidate.reservation_id,
                    candidate.user_id,
                    message_builder(candidate),
                    sent_at=sent_at,
                )
                if result.sent:
                    sent_reservation_ids.append(candidate.reservation_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return ReminderTaskResult(sent_reservation_ids=sent_reservation_ids)

    def _normalize_now(self, now: datetime | None) -> datetime:
        current = now or datetime.now()
        return current.replace(second=0, microsecond=0)

    def _build_reservation_reminder_message(self, reservation: NotificationReservationSnapshot) -> str:
        return (
            "您的自习室预约即将开始，请按时到场签到。\n"
            f"预约 ID：{reservation.reservation_id}\n"
            f"自习室：{reservation.room_name}\n"
            f"座位：{self._format_seat(reservation)}\n"
            f"开始时间：{self._format_datetime(reservation.start_time)}\n"
            f"结束时间：{self._format_datetime(reservation.end_time)}"
        )

    def _build_no_show_reminder_message(self, reservation: NotificationReservationSnapshot) -> str:
        return (
            "您的自习室预约已经开始，但系统尚未记录签到，请尽快完成签到。\n"
            f"预约 ID：{reservation.reservation_id}\n"
            f"自习室：{reservation.room_name}\n"
            f"座位：{self._format_seat(reservation)}\n"
            f"开始时间：{self._format_datetime(reservation.start_time)}\n"
            f"结束时间：{self._format_datetime(reservation.end_time)}"
        )

    def _build_auto_cancel_message(self, reservation: NotificationReservationSnapshot) -> str:
        return (
            "您的自习室预约已因超时未签到被自动取消，座位已释放。\n"
            f"预约 ID：{reservation.reservation_id}\n"
            f"自习室：{reservation.room_name}\n"
            f"座位：{self._format_seat(reservation)}\n"
            f"开始时间：{self._format_datetime(reservation.start_time)}\n"
            f"结束时间：{self._format_datetime(reservation.end_time)}"
        )

    def _format_datetime(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M")

    def _format_seat(self, reservation: NotificationReservationSnapshot) -> str:
        if reservation.seat_label == reservation.seat_code:
            return reservation.seat_code
        return f"{reservation.seat_label}（{reservation.seat_code}）"
