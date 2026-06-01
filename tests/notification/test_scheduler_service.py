from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, time

from sqlalchemy import func, select

from app.core.config import Settings
from app.core.database import SessionLocal
from app.modules.notification.models.notification_log import (
    NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE,
    NOTIFICATION_TYPE_NO_SHOW_REMINDER,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
    NotificationLog,
)
from app.modules.notification.services.scheduler_service import (
    TASK_AUTO_CANCEL_NOTIFICATIONS,
    TASK_EXPIRED_RELEASE,
    TASK_NO_SHOW_REMINDERS,
    TASK_RESERVATION_REMINDERS,
    run_scheduler_loop,
    tick,
)
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.violation.models.violation_record import ViolationRecord


def _seed_scheduler_reservations(seed_data: dict, *, now: datetime) -> dict[str, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Scheduler Room",
            location="Engineering Scheduler",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        reminder_seat = Seat(
            room_id=room.id,
            seat_code="SCH-01",
            seat_label="Reminder Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        no_show_seat = Seat(
            room_id=room.id,
            seat_code="SCH-02",
            seat_label="No Show Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        timeout_seat = Seat(
            room_id=room.id,
            seat_code="SCH-03",
            seat_label="Timeout Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add_all([reminder_seat, no_show_seat, timeout_seat])
        session.flush()

        reminder_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=reminder_seat.id,
            room_id=room.id,
            start_time=now + timedelta(minutes=15),
            end_time=now + timedelta(hours=1),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        no_show_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=no_show_seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=10),
            end_time=now + timedelta(minutes=50),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        timeout_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=timeout_seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=15),
            end_time=now + timedelta(minutes=45),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add_all([reminder_reservation, no_show_reservation, timeout_reservation])
        session.commit()
        return {
            "reminder": reminder_reservation.id,
            "no_show": no_show_reservation.id,
            "timeout": timeout_reservation.id,
        }


def _notification_count(reservation_id: int, notification_type: str) -> int:
    with SessionLocal() as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(NotificationLog)
                .where(
                    NotificationLog.reservation_id == reservation_id,
                    NotificationLog.notification_type == notification_type,
                ),
            )
            or 0,
        )


def test_scheduler_tick_runs_all_tasks_in_order_and_keeps_idempotent(seed_data: dict) -> None:
    now = datetime.now().replace(second=0, microsecond=0)
    reservation_ids = _seed_scheduler_reservations(seed_data, now=now)

    first = tick(now=now)
    second = tick(now=now + timedelta(minutes=1))

    assert [outcome.task_name for outcome in first.outcomes] == [
        TASK_RESERVATION_REMINDERS,
        TASK_NO_SHOW_REMINDERS,
        TASK_EXPIRED_RELEASE,
        TASK_AUTO_CANCEL_NOTIFICATIONS,
    ]
    assert all(outcome.success for outcome in first.outcomes)
    assert first.reservation_reminder_ids == [reservation_ids["reminder"]]
    assert first.no_show_reminder_ids == [reservation_ids["timeout"], reservation_ids["no_show"]]
    assert first.expired_reservation_ids == [reservation_ids["timeout"]]
    assert first.timeout_release_notification_ids == [reservation_ids["timeout"]]

    assert second.reservation_reminder_ids == []
    assert second.no_show_reminder_ids == []
    assert second.expired_reservation_ids == []
    assert second.timeout_release_notification_ids == []

    with SessionLocal() as session:
        timeout_reservation = session.get(Reservation, reservation_ids["timeout"])
        timeout_violation_count = int(
            session.scalar(
                select(func.count())
                .select_from(ViolationRecord)
                .where(ViolationRecord.reservation_id == reservation_ids["timeout"]),
            )
            or 0,
        )

    assert timeout_reservation is not None and timeout_reservation.status == RESERVATION_STATUS_EXPIRED
    assert timeout_violation_count == 1
    assert _notification_count(reservation_ids["reminder"], NOTIFICATION_TYPE_RESERVATION_REMINDER) == 1
    assert _notification_count(reservation_ids["no_show"], NOTIFICATION_TYPE_NO_SHOW_REMINDER) == 1
    assert _notification_count(reservation_ids["timeout"], NOTIFICATION_TYPE_NO_SHOW_REMINDER) == 1
    assert _notification_count(reservation_ids["timeout"], NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE) == 1


def test_scheduler_loop_runs_tasks_immediately_when_started(seed_data: dict) -> None:
    now = datetime.now().replace(second=0, microsecond=0)
    reservation_ids = _seed_scheduler_reservations(seed_data, now=now)

    async def exercise_loop_once() -> None:
        task = asyncio.create_task(
            run_scheduler_loop(
                settings=Settings(task_scheduler_interval_seconds=60),
                session_factory=SessionLocal,
            )
        )
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(exercise_loop_once())

    with SessionLocal() as session:
        timeout_reservation = session.get(Reservation, reservation_ids["timeout"])
        timeout_violation_count = int(
            session.scalar(
                select(func.count())
                .select_from(ViolationRecord)
                .where(ViolationRecord.reservation_id == reservation_ids["timeout"]),
            )
            or 0,
        )

    assert timeout_reservation is not None and timeout_reservation.status == RESERVATION_STATUS_EXPIRED
    assert timeout_violation_count == 1
    assert _notification_count(reservation_ids["timeout"], NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE) == 1
