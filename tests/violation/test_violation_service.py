from __future__ import annotations

from datetime import datetime, timedelta, time

from app.core.database import SessionLocal
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)
from app.modules.violation.services.checkin_violation_service import CheckinViolationService


def _seed_reservation(seed_data: dict, *, status: str, occurred_at: datetime | None = None) -> tuple[int, datetime]:
    violation_time = occurred_at or datetime.now().replace(second=0, microsecond=0)
    with SessionLocal() as session:
        room = StudyRoom(
            name=f"Violation Room {status}",
            location="Engineering 701",
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
            seat_code=f"V-{status[:3]}",
            seat_label=f"Seat {status}",
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
            start_time=violation_time - timedelta(hours=1),
            end_time=violation_time,
            status=status,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by="STUDENT" if status == RESERVATION_STATUS_CANCELLED else None,
            cancel_reason="Cancelled by student." if status == RESERVATION_STATUS_CANCELLED else None,
        )
        session.add(reservation)
        session.commit()
        return reservation.id, violation_time


def test_checkin_public_service_records_timeout_violation_idempotently(seed_data: dict):
    reservation_id, violation_time = _seed_reservation(
        seed_data,
        status=RESERVATION_STATUS_EXPIRED,
    )

    with SessionLocal() as session:
        service = CheckinViolationService(session)
        service.record_missed_checkin(
            reservation_id=reservation_id,
            user_id=seed_data["users"]["student"],
            occurred_at=violation_time,
        )
        service.record_missed_checkin(
            reservation_id=reservation_id,
            user_id=seed_data["users"]["student"],
            occurred_at=violation_time + timedelta(minutes=1),
        )
        session.commit()

    with SessionLocal() as session:
        records = list(
            session.query(ViolationRecord)
            .filter(ViolationRecord.reservation_id == reservation_id)
            .all(),
        )

    assert len(records) == 1
    assert records[0].user_id == seed_data["users"]["student"]
    assert records[0].violation_type == VIOLATION_TYPE_NO_SHOW_TIMEOUT
    assert records[0].occurred_at == violation_time


def test_checked_in_and_cancelled_reservations_do_not_generate_violations(seed_data: dict):
    checked_in_reservation_id, occurred_at = _seed_reservation(
        seed_data,
        status=RESERVATION_STATUS_CHECKED_IN,
    )
    cancelled_reservation_id, _ = _seed_reservation(
        seed_data,
        status=RESERVATION_STATUS_CANCELLED,
        occurred_at=occurred_at + timedelta(minutes=5),
    )

    with SessionLocal() as session:
        service = CheckinViolationService(session)
        service.record_missed_checkin(
            reservation_id=checked_in_reservation_id,
            user_id=seed_data["users"]["student"],
            occurred_at=occurred_at,
        )
        service.record_missed_checkin(
            reservation_id=cancelled_reservation_id,
            user_id=seed_data["users"]["student"],
            occurred_at=occurred_at + timedelta(minutes=5),
        )
        session.commit()

    with SessionLocal() as session:
        count = (
            session.query(ViolationRecord)
            .filter(ViolationRecord.reservation_id.in_([checked_in_reservation_id, cancelled_reservation_id]))
            .count()
        )

    assert count == 0
