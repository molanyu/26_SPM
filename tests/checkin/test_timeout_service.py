from __future__ import annotations

from datetime import datetime, timedelta, time

from app.core.database import SessionLocal
from app.modules.checkin.tasks.timeout_release_task import release_expired_reservations
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.violation.models.violation_record import ViolationRecord


class StubViolationService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def record_missed_checkin(self, *, reservation_id: int, user_id: int, occurred_at: datetime) -> None:
        self.calls.append(
            {
                "reservation_id": reservation_id,
                "user_id": user_id,
                "occurred_at": occurred_at,
            },
        )


def _seed_timeout_reservations(seed_data: dict):
    now = datetime.now().replace(second=0, microsecond=0)
    with SessionLocal() as session:
        room = StudyRoom(
            name="Timeout Room",
            location="Engineering 601",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        overdue_seat = Seat(
            room_id=room.id,
            seat_code="T-01",
            seat_label="Overdue Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        upcoming_seat = Seat(
            room_id=room.id,
            seat_code="T-02",
            seat_label="Upcoming Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add_all([overdue_seat, upcoming_seat])
        session.flush()

        overdue_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=overdue_seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=20),
            end_time=now + timedelta(minutes=40),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        upcoming_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=upcoming_seat.id,
            room_id=room.id,
            start_time=now - timedelta(minutes=5),
            end_time=now + timedelta(minutes=55),
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add_all([overdue_reservation, upcoming_reservation])
        session.commit()
        return now, overdue_reservation.id, upcoming_reservation.id


def test_timeout_release_marks_overdue_reservations_expired_and_triggers_violation(seed_data: dict):
    now, overdue_reservation_id, upcoming_reservation_id = _seed_timeout_reservations(seed_data)
    violation_service = StubViolationService()

    with SessionLocal() as session:
        result = release_expired_reservations(
            session,
            now=now,
            violation_service=violation_service,
        )

    assert result.expired_reservation_ids == [overdue_reservation_id]
    assert [call["reservation_id"] for call in violation_service.calls] == [overdue_reservation_id]

    with SessionLocal() as session:
        overdue_reservation = session.get(Reservation, overdue_reservation_id)
        upcoming_reservation = session.get(Reservation, upcoming_reservation_id)
    assert overdue_reservation is not None and overdue_reservation.status == "EXPIRED"
    assert upcoming_reservation is not None and upcoming_reservation.status == "BOOKED"


def test_timeout_release_with_default_violation_service_persists_violation_record(seed_data: dict):
    now, overdue_reservation_id, upcoming_reservation_id = _seed_timeout_reservations(seed_data)

    with SessionLocal() as session:
        result = release_expired_reservations(session, now=now)

    assert result.expired_reservation_ids == [overdue_reservation_id]

    with SessionLocal() as session:
        overdue_reservation = session.get(Reservation, overdue_reservation_id)
        upcoming_reservation = session.get(Reservation, upcoming_reservation_id)
        violation_records = (
            session.query(ViolationRecord)
            .filter(ViolationRecord.reservation_id == overdue_reservation_id)
            .all()
        )

    assert overdue_reservation is not None and overdue_reservation.status == "EXPIRED"
    assert upcoming_reservation is not None and upcoming_reservation.status == "BOOKED"
    assert len(violation_records) == 1
    assert violation_records[0].reservation_id == overdue_reservation_id
    assert violation_records[0].user_id == seed_data["users"]["student"]
