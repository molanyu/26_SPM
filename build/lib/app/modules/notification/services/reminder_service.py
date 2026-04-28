from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.modules.notification.models.notification_log import (
    NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE,
    NOTIFICATION_TYPE_NO_SHOW_REMINDER,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
)
from app.modules.notification.services.notification_service import NotificationService
from app.modules.reservation.services.notification_access_service import (
    NotificationReservationService,
    NotificationReservationSnapshot,
)


@dataclass(slots=True)
class ReminderTaskResult:
    sent_reservation_ids: list[int]


class ReminderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.notification_service = NotificationService(session)
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
            f"Reservation {reservation.reservation_id} starts at "
            f"{reservation.start_time.strftime('%Y-%m-%d %H:%M')}."
        )

    def _build_no_show_reminder_message(self, reservation: NotificationReservationSnapshot) -> str:
        return (
            f"Reservation {reservation.reservation_id} started at "
            f"{reservation.start_time.strftime('%Y-%m-%d %H:%M')} and is still awaiting check-in."
        )

    def _build_auto_cancel_message(self, reservation: NotificationReservationSnapshot) -> str:
        return f"Reservation {reservation.reservation_id} was automatically cancelled after missed check-in."
