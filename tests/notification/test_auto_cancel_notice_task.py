from __future__ import annotations

from datetime import datetime, timedelta, time

from app.core.database import SessionLocal
from app.modules.notification.models.notification_log import (
    NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE,
    NotificationLog,
)
from app.modules.notification.tasks.auto_cancel_notice_task import send_auto_cancel_notifications
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


def _seed_reservations(seed_data: dict, *, now: datetime) -> tuple[int, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Auto Cancel Room",
            location="Engineering 904",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        expired_seat = Seat(
            room_id=room.id,
            seat_code="AC-01",
            seat_label="Expired Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        booked_seat = Seat(
            room_id=room.id,
            seat_code="AC-02",
            seat_label="Booked Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add_all([expired_seat, booked_seat])
        session.flush()

        expired_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=expired_seat.id,
            room_id=room.id,
            start_time=now - timedelta(hours=1),
            end_time=now,
            status=RESERVATION_STATUS_EXPIRED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        booked_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=booked_seat.id,
            room_id=room.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add_all([expired_reservation, booked_reservation])
        session.commit()
        return expired_reservation.id, booked_reservation.id


def test_auto_cancel_notice_task_is_idempotent_and_only_notifies_expired_reservations(seed_data: dict):
    now = datetime.now().replace(second=0, microsecond=0)
    expired_id, booked_id = _seed_reservations(seed_data, now=now)

    with SessionLocal() as session:
        first = send_auto_cancel_notifications(session, now=now)

    with SessionLocal() as session:
        second = send_auto_cancel_notifications(session, now=now + timedelta(minutes=1))

    assert first.sent_reservation_ids == [expired_id]
    assert second.sent_reservation_ids == []

    with SessionLocal() as session:
        logs = (
            session.query(NotificationLog)
            .filter(NotificationLog.notification_type == NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE)
            .all()
        )

    assert len(logs) == 1
    assert logs[0].reservation_id == expired_id
    assert logs[0].reservation_id != booked_id
