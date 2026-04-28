from __future__ import annotations

from datetime import datetime, timedelta, time

from app.core.config import Settings
from app.core.database import SessionLocal
from app.modules.notification.models.notification_log import (
    NOTIFICATION_CHANNEL_SMTP_EMAIL,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
    NotificationLog,
)
from app.modules.notification.services.reminder_service import ReminderService
from app.modules.notification.tasks.reservation_reminder_task import send_reservation_reminders
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


class FakeEmailSender:
    def __init__(self) -> None:
        self.deliveries: list[dict[str, str]] = []

    def send_email(self, *, to_email: str, subject: str, body: str) -> None:
        self.deliveries.append(
            {
                "to_email": to_email,
                "subject": subject,
                "body": body,
            }
        )


def _build_smtp_settings() -> Settings:
    return Settings(
        notification_default_channel="smtp_email",
        smtp_host="smtp.example.com",
        smtp_port="587",
        smtp_from_email="noreply@example.com",
        smtp_use_tls=True,
        smtp_timeout_seconds="10",
    )


def _seed_reservations(seed_data: dict, *, now: datetime, user_id: int | None = None) -> tuple[int, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Reminder Room",
            location="Engineering 902",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        due_seat = Seat(
            room_id=room.id,
            seat_code="RR-01",
            seat_label="Due Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        outside_seat = Seat(
            room_id=room.id,
            seat_code="RR-02",
            seat_label="Outside Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add_all([due_seat, outside_seat])
        session.flush()

        due_reservation = Reservation(
            user_id=user_id or seed_data["users"]["student"],
            seat_id=due_seat.id,
            room_id=room.id,
            start_time=now + timedelta(minutes=15),
            end_time=now + timedelta(hours=1, minutes=15),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        outside_reservation = Reservation(
            user_id=user_id or seed_data["users"]["student"],
            seat_id=outside_seat.id,
            room_id=room.id,
            start_time=now + timedelta(minutes=16),
            end_time=now + timedelta(hours=1, minutes=16),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add_all([due_reservation, outside_reservation])
        session.commit()
        return due_reservation.id, outside_reservation.id


def test_reservation_reminder_task_only_sends_for_the_target_window(seed_data: dict):
    now = datetime.now().replace(second=0, microsecond=0)
    due_reservation_id, outside_reservation_id = _seed_reservations(seed_data, now=now)

    with SessionLocal() as session:
        first = send_reservation_reminders(session, now=now)

    with SessionLocal() as session:
        second = send_reservation_reminders(session, now=now)

    assert first.sent_reservation_ids == [due_reservation_id]
    assert second.sent_reservation_ids == []

    with SessionLocal() as session:
        logs = (
            session.query(NotificationLog)
            .filter(NotificationLog.notification_type == NOTIFICATION_TYPE_RESERVATION_REMINDER)
            .all()
        )

    assert len(logs) == 1
    assert logs[0].reservation_id == due_reservation_id
    assert logs[0].reservation_id != outside_reservation_id


def test_reservation_reminder_task_keeps_idempotent_under_smtp_email(seed_data: dict):
    now = datetime.now().replace(second=0, microsecond=0)
    due_reservation_id, _outside_reservation_id = _seed_reservations(
        seed_data,
        now=now,
        user_id=seed_data["users"]["target"],
    )
    fake_sender = FakeEmailSender()

    with SessionLocal() as session:
        service = ReminderService(
            session,
            settings=_build_smtp_settings(),
            email_sender=fake_sender,
        )
        first = service.send_reservation_reminders(now=now)

    with SessionLocal() as session:
        service = ReminderService(
            session,
            settings=_build_smtp_settings(),
            email_sender=fake_sender,
        )
        second = service.send_reservation_reminders(now=now)

    assert first.sent_reservation_ids == [due_reservation_id]
    assert second.sent_reservation_ids == []
    assert len(fake_sender.deliveries) == 1
    assert fake_sender.deliveries[0]["to_email"] == seed_data["credentials"]["target_email"]

    with SessionLocal() as session:
        logs = (
            session.query(NotificationLog)
            .filter(NotificationLog.notification_type == NOTIFICATION_TYPE_RESERVATION_REMINDER)
            .all()
        )

    assert len(logs) == 1
    assert logs[0].reservation_id == due_reservation_id
    assert logs[0].channel == NOTIFICATION_CHANNEL_SMTP_EMAIL
