from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, time
from pathlib import Path
from threading import Barrier
from time import sleep
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.database import Base, SessionLocal
from app.modules.identity.models.department import Department
from app.modules.identity.models.user import User
from app.modules.identity.schemas.user import UserCreateRequest
from app.modules.identity.services.user_service import UserService
from app.modules.notification.models.notification_log import (
    NOTIFICATION_CHANNEL_SMTP_EMAIL,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_PENDING,
    NOTIFICATION_STATUS_SENT,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
    NotificationLog,
)
from app.modules.notification.repositories.notification_repository import NotificationRepository
from app.modules.notification.services.notification_service import NotificationService
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


def _build_smtp_settings(**overrides: object) -> Settings:
    base = {
        "notification_default_channel": "smtp_email",
        "smtp_host": "smtp.example.com",
        "smtp_port": "587",
        "smtp_from_email": "noreply@example.com",
        "smtp_use_tls": True,
        "smtp_timeout_seconds": "10",
    }
    base.update(overrides)
    return Settings(**base)


def _seed_reservation(seed_data: dict, *, user_id: int | None = None) -> int:
    now = datetime.now().replace(second=0, microsecond=0)
    with SessionLocal() as session:
        room = StudyRoom(
            name="Notification Service Room",
            location="Engineering 901",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        seat = Seat(
            room_id=room.id,
            seat_code="NS-01",
            seat_label="Notification Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.flush()

        reservation = Reservation(
            user_id=user_id or seed_data["users"]["student"],
            seat_id=seat.id,
            room_id=room.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.commit()
        return reservation.id


def _build_notification_session_factory():
    database_path = Path(f"notification_service_{uuid4().hex}.db")
    engine = create_engine(
        f"sqlite:///{database_path}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    local_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    Base.metadata.create_all(bind=engine)
    return engine, local_session, database_path


def _seed_local_reservation(local_session) -> tuple[int, int]:
    now = datetime.now().replace(second=0, microsecond=0)
    with local_session() as session:
        department = Department(name="Concurrency Department", code="NTF-CS", is_active=True)
        user = User(
            student_no="20249999",
            name="Concurrent Student",
            password_hash="hashed-password",
            department=department,
            is_active=True,
        )
        room = StudyRoom(
            name="Concurrency Room",
            location="Engineering 905",
            department_id=None,
            is_department_only=False,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add_all([department, user, room])
        session.flush()

        seat = Seat(
            room_id=room.id,
            seat_code="CC-01",
            seat_label="Concurrency Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.flush()

        reservation = Reservation(
            user_id=user.id,
            seat_id=seat.id,
            room_id=room.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.commit()
        return reservation.id, user.id


def test_send_notification_is_idempotent_and_persists_notification_log(seed_data: dict):
    reservation_id = _seed_reservation(seed_data)
    sent_at = datetime.now().replace(second=0, microsecond=0)

    with SessionLocal() as session:
        service = NotificationService(session)
        first = service.send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["student"],
            "Reservation reminder message.",
            sent_at=sent_at,
        )
        second = service.send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["student"],
            "Reservation reminder message.",
            sent_at=sent_at + timedelta(minutes=1),
        )

    assert first.sent is True
    assert second.sent is False
    assert first.log.id == second.log.id

    with SessionLocal() as session:
        logs = (
            session.query(NotificationLog)
            .filter(
                NotificationLog.reservation_id == reservation_id,
                NotificationLog.notification_type == NOTIFICATION_TYPE_RESERVATION_REMINDER,
            )
            .all()
        )

    assert len(logs) == 1
    assert logs[0].message == "Reservation reminder message."
    assert logs[0].status == NOTIFICATION_STATUS_SENT


def test_send_notification_uses_smtp_email_channel_when_enabled(seed_data: dict):
    reservation_id = _seed_reservation(seed_data, user_id=seed_data["users"]["target"])
    sent_at = datetime.now().replace(second=0, microsecond=0)
    fake_sender = FakeEmailSender()

    with SessionLocal() as session:
        result = NotificationService(
            session,
            settings=_build_smtp_settings(),
            email_sender=fake_sender,
        ).send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["target"],
            "SMTP reminder message.",
            sent_at=sent_at,
        )

    assert result.sent is True
    assert result.log.channel == NOTIFICATION_CHANNEL_SMTP_EMAIL
    assert result.log.status == NOTIFICATION_STATUS_SENT
    assert fake_sender.deliveries == [
        {
            "to_email": seed_data["credentials"]["target_email"],
            "subject": "自习室预约即将开始提醒",
            "body": "SMTP reminder message.",
        }
    ]


def test_send_notification_uses_student_notification_email_for_smtp(seed_data: dict):
    with SessionLocal() as session:
        created_student = UserService(session).create_user(
            UserCreateRequest(
                account_type="student",
                name="SMTP Student",
                student_no="20249991",
                notification_email="smtp.student@example.com",
                password="smtp-student-pass",
                department_id=seed_data["departments"]["cs"],
            )
        )

    reservation_id = _seed_reservation(seed_data, user_id=created_student.id)
    sent_at = datetime.now().replace(second=0, microsecond=0)
    fake_sender = FakeEmailSender()

    with SessionLocal() as session:
        result = NotificationService(
            session,
            settings=_build_smtp_settings(),
            email_sender=fake_sender,
        ).send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            created_student.id,
            "SMTP reminder message.",
            sent_at=sent_at,
        )

    assert result.sent is True
    assert result.log.channel == NOTIFICATION_CHANNEL_SMTP_EMAIL
    assert result.log.status == NOTIFICATION_STATUS_SENT
    assert fake_sender.deliveries == [
        {
            "to_email": "smtp.student@example.com",
            "subject": "自习室预约即将开始提醒",
            "body": "SMTP reminder message.",
        }
    ]


def test_send_notification_fails_when_smtp_configuration_is_missing(seed_data: dict):
    reservation_id = _seed_reservation(seed_data, user_id=seed_data["users"]["target"])
    sent_at = datetime.now().replace(second=0, microsecond=0)

    with SessionLocal() as session:
        result = NotificationService(
            session,
            settings=_build_smtp_settings(smtp_host=None),
        ).send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["target"],
            "SMTP reminder message.",
            sent_at=sent_at,
        )

    assert result.sent is False
    assert result.log.channel == NOTIFICATION_CHANNEL_SMTP_EMAIL
    assert result.log.status == NOTIFICATION_STATUS_FAILED


def test_send_notification_fails_when_target_has_no_usable_email(seed_data: dict):
    reservation_id = _seed_reservation(seed_data)
    sent_at = datetime.now().replace(second=0, microsecond=0)
    fake_sender = FakeEmailSender()

    with SessionLocal() as session:
        result = NotificationService(
            session,
            settings=_build_smtp_settings(),
            email_sender=fake_sender,
        ).send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["student"],
            "SMTP reminder message.",
            sent_at=sent_at,
        )

    assert result.sent is False
    assert result.log.channel == NOTIFICATION_CHANNEL_SMTP_EMAIL
    assert result.log.status == NOTIFICATION_STATUS_FAILED
    assert fake_sender.deliveries == []


def test_send_notification_claims_before_mock_send_under_concurrency(monkeypatch: pytest.MonkeyPatch):
    engine, local_session, database_path = _build_notification_session_factory()
    try:
        reservation_id, user_id = _seed_local_reservation(local_session)
        sent_at = datetime.now().replace(second=0, microsecond=0)
        barrier = Barrier(2)
        send_calls: list[int] = []

        def slow_mock_send(self, payload, attempt_sent_at):
            send_calls.append(payload.reservation_id)
            sleep(0.2)

        monkeypatch.setattr(NotificationService, "_mock_send", slow_mock_send)

        def attempt_send() -> tuple[bool, str]:
            with local_session() as session:
                service = NotificationService(session)
                barrier.wait()
                result = service.send_notification(
                    NOTIFICATION_TYPE_RESERVATION_REMINDER,
                    reservation_id,
                    user_id,
                    "Concurrent reminder message.",
                    sent_at=sent_at,
                )
                return result.sent, result.log.status

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: attempt_send(), range(2)))

        assert len(send_calls) == 1
        assert sum(1 for sent, _ in results if sent) == 1
        assert sum(1 for sent, _ in results if not sent) == 1

        with local_session() as session:
            logs = (
                session.query(NotificationLog)
                .filter(
                    NotificationLog.reservation_id == reservation_id,
                    NotificationLog.notification_type == NOTIFICATION_TYPE_RESERVATION_REMINDER,
                )
                .all()
            )

        assert len(logs) == 1
        assert logs[0].status == NOTIFICATION_STATUS_SENT
    finally:
        engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_send_notification_marks_failed_attempts_and_retries(seed_data: dict, monkeypatch: pytest.MonkeyPatch):
    reservation_id = _seed_reservation(seed_data)
    first_sent_at = datetime.now().replace(second=0, microsecond=0)
    retry_sent_at = first_sent_at + timedelta(minutes=1)
    attempts = {"count": 0}

    def flaky_mock_send(self, payload, sent_at):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("mock send failed")

    monkeypatch.setattr(NotificationService, "_mock_send", flaky_mock_send)

    with SessionLocal() as session:
        first = NotificationService(session).send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["student"],
            "Retry reminder message.",
            sent_at=first_sent_at,
        )
        first_status = first.log.status

    with SessionLocal() as session:
        second = NotificationService(session).send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["student"],
            "Retry reminder message.",
            sent_at=retry_sent_at,
        )

    assert first.sent is False
    assert first_status == NOTIFICATION_STATUS_FAILED
    assert second.sent is True
    assert second.log.status == NOTIFICATION_STATUS_SENT
    assert attempts["count"] == 2

    with SessionLocal() as session:
        logs = (
            session.query(NotificationLog)
            .filter(
                NotificationLog.reservation_id == reservation_id,
                NotificationLog.notification_type == NOTIFICATION_TYPE_RESERVATION_REMINDER,
            )
            .all()
        )

    assert len(logs) == 1
    assert logs[0].status == NOTIFICATION_STATUS_SENT
    assert logs[0].sent_at == retry_sent_at


def test_send_notification_keeps_pending_log_when_finalize_write_fails(
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    reservation_id = _seed_reservation(seed_data)
    sent_at = datetime.now().replace(second=0, microsecond=0)
    send_calls = {"count": 0}
    finalize_failures = {"remaining": 1}
    original_transition_status = NotificationRepository.transition_status

    def tracked_mock_send(self, payload, attempt_sent_at):
        send_calls["count"] += 1

    def flaky_transition_status(self, notification_log_id, **kwargs):
        if kwargs["to_status"] == NOTIFICATION_STATUS_SENT and finalize_failures["remaining"] > 0:
            finalize_failures["remaining"] -= 1
            raise RuntimeError("notification finalize write failed")
        return original_transition_status(self, notification_log_id, **kwargs)

    monkeypatch.setattr(NotificationService, "_mock_send", tracked_mock_send)
    monkeypatch.setattr(NotificationRepository, "transition_status", flaky_transition_status)

    with SessionLocal() as session:
        with pytest.raises(RuntimeError, match="could not be finalized after send"):
            NotificationService(session).send_notification(
                NOTIFICATION_TYPE_RESERVATION_REMINDER,
                reservation_id,
                seed_data["users"]["student"],
                "Pending reminder message.",
                sent_at=sent_at,
            )

    with SessionLocal() as session:
        second = NotificationService(session).send_notification(
            NOTIFICATION_TYPE_RESERVATION_REMINDER,
            reservation_id,
            seed_data["users"]["student"],
            "Pending reminder message.",
            sent_at=sent_at + timedelta(minutes=1),
        )

    assert second.sent is False
    assert second.log.status == NOTIFICATION_STATUS_PENDING
    assert send_calls["count"] == 1
