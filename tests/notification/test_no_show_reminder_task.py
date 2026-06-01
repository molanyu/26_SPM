from __future__ import annotations

from datetime import datetime, timedelta, time

from app.core.database import SessionLocal
from app.modules.notification.models.notification_log import (
    NOTIFICATION_TYPE_NO_SHOW_REMINDER,
    NotificationLog,
)
from app.modules.notification.tasks.no_show_reminder_task import send_no_show_reminders
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


def _seed_reservations(seed_data: dict, *, now: datetime) -> tuple[int, int, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="No Show Room",
            location="Engineering 903",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        booked_seat = Seat(
            room_id=room.id,
            seat_code="NSR-01",
            seat_label="Booked Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        checked_in_seat = Seat(
            room_id=room.id,
            seat_code="NSR-02",
            seat_label="Checked In Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        cancelled_seat = Seat(
            room_id=room.id,
            seat_code="NSR-03",
            seat_label="Cancelled Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add_all([booked_seat, checked_in_seat, cancelled_seat])
        session.flush()

        booked_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=booked_seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=10),
            end_time=now + timedelta(minutes=50),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        checked_in_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=checked_in_seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=10),
            end_time=now + timedelta(minutes=50),
            status=RESERVATION_STATUS_CHECKED_IN,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        cancelled_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=cancelled_seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=10),
            end_time=now + timedelta(minutes=50),
            status=RESERVATION_STATUS_CANCELLED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by="STUDENT",
            cancel_reason="Cancelled by student.",
        )
        session.add_all([booked_reservation, checked_in_reservation, cancelled_reservation])
        session.commit()
        return booked_reservation.id, checked_in_reservation.id, cancelled_reservation.id


def _seed_delayed_no_show_reservation(seed_data: dict, *, now: datetime) -> int:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Delayed No Show Room",
            location="Engineering 904",
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
            seat_code="DNS-01",
            seat_label="Delayed Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.flush()

        reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=13),
            end_time=now + timedelta(minutes=47),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.commit()
        return reservation.id


def test_no_show_reminder_task_skips_checked_in_and_cancelled_reservations(seed_data: dict):
    now = datetime.now().replace(second=0, microsecond=0)
    booked_id, checked_in_id, cancelled_id = _seed_reservations(seed_data, now=now)

    with SessionLocal() as session:
        first = send_no_show_reminders(session, now=now)

    with SessionLocal() as session:
        second = send_no_show_reminders(session, now=now)

    assert first.sent_reservation_ids == [booked_id]
    assert second.sent_reservation_ids == []

    with SessionLocal() as session:
        logs = (
            session.query(NotificationLog)
            .filter(NotificationLog.notification_type == NOTIFICATION_TYPE_NO_SHOW_REMINDER)
            .all()
        )

    assert len(logs) == 1
    assert logs[0].reservation_id == booked_id
    assert logs[0].reservation_id not in {checked_in_id, cancelled_id}


def test_no_show_reminder_task_backfills_after_scheduler_delay(seed_data: dict):
    now = datetime.now().replace(second=0, microsecond=0)
    delayed_reservation_id = _seed_delayed_no_show_reservation(seed_data, now=now)

    with SessionLocal() as session:
        first = send_no_show_reminders(session, now=now)

    with SessionLocal() as session:
        second = send_no_show_reminders(session, now=now + timedelta(minutes=1))

    assert first.sent_reservation_ids == [delayed_reservation_id]
    assert second.sent_reservation_ids == []

    with SessionLocal() as session:
        logs = (
            session.query(NotificationLog)
            .filter(NotificationLog.notification_type == NOTIFICATION_TYPE_NO_SHOW_REMINDER)
            .all()
        )

    assert len(logs) == 1
    assert logs[0].reservation_id == delayed_reservation_id
