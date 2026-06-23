from __future__ import annotations

from datetime import datetime, timedelta, time

from app.core.database import SessionLocal
from app.modules.identity.models.user import User
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.system_config.services.config_service import ConfigService
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)
from app.modules.violation.models.user_reservation_block import UserReservationBlock
from app.modules.violation.services.checkin_violation_service import CheckinViolationService
from app.modules.violation.services.violation_service import ViolationService


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


def _seed_timeout_violation(seed_data: dict, *, occurred_at: datetime) -> int:
    reservation_id, _ = _seed_reservation(
        seed_data,
        status=RESERVATION_STATUS_EXPIRED,
        occurred_at=occurred_at,
    )
    with SessionLocal() as session:
        service = CheckinViolationService(session)
        service.record_missed_checkin(
            reservation_id=reservation_id,
            user_id=seed_data["users"]["student"],
            occurred_at=occurred_at,
        )
        session.commit()
    return reservation_id


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


def test_penalty_status_does_not_double_count_repeated_timeout_recording_for_same_reservation(client, seed_data: dict):
    as_of = datetime(2026, 6, 16, 12, 0, 0)
    reservation_id, violation_time = _seed_reservation(
        seed_data,
        status=RESERVATION_STATUS_EXPIRED,
        occurred_at=as_of - timedelta(days=1),
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
        ConfigService(session).list_configs()
        status = ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )
        session.commit()

    assert status.violation_count == 1
    assert status.is_penalized is False


def test_penalty_status_is_false_when_threshold_not_reached(client, seed_data: dict):
    as_of = datetime(2026, 6, 16, 12, 0, 0)
    _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=2))
    _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=1))

    with SessionLocal() as session:
        ConfigService(session).list_configs()
        status = ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )

    assert status.is_penalized is False
    assert status.violation_count == 2
    assert status.window_start == as_of - timedelta(days=30)
    assert status.window_end == as_of
    assert status.penalty_start is None
    assert status.penalty_end is None


def test_penalty_status_is_true_when_threshold_reached_and_penalty_active(client, seed_data: dict):
    as_of = datetime(2026, 6, 16, 12, 0, 0)
    first = as_of - timedelta(days=4)
    second = as_of - timedelta(days=3)
    third = as_of - timedelta(days=2)
    for occurred_at in [third, first, second]:
        _seed_timeout_violation(seed_data, occurred_at=occurred_at)

    with SessionLocal() as session:
        ConfigService(session).list_configs()
        status = ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )

    assert status.is_penalized is True
    assert status.violation_count == 3
    assert status.penalty_start == third
    assert status.penalty_end == third + timedelta(days=7)


def test_penalty_status_is_false_when_penalty_has_expired(client, seed_data: dict):
    as_of = datetime(2026, 6, 16, 12, 0, 0)
    first = as_of - timedelta(days=12)
    second = as_of - timedelta(days=11)
    third = as_of - timedelta(days=10)
    for occurred_at in [first, second, third]:
        _seed_timeout_violation(seed_data, occurred_at=occurred_at)

    with SessionLocal() as session:
        ConfigService(session).list_configs()
        status = ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )

    assert status.violation_count == 3
    assert status.penalty_start == third
    assert status.penalty_end == third + timedelta(days=7)
    assert status.is_penalized is False


def test_penalty_status_uses_system_config_values(client, seed_data: dict):
    as_of = datetime(2026, 6, 16, 12, 0, 0)
    _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=8))
    _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=1))

    with SessionLocal() as session:
        config_service = ConfigService(session)
        config_service.list_configs()
        config_service.update_config("violation_penalty_threshold_count", 2)
        config_service.update_config("violation_penalty_window_days", 10)
        config_service.update_config("violation_penalty_duration_days", 3)
        status = ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )

    assert status.violation_count == 2
    assert status.window_start == as_of - timedelta(days=10)
    assert status.penalty_start == as_of - timedelta(days=1)
    assert status.penalty_end == as_of - timedelta(days=1) + timedelta(days=3)
    assert status.is_penalized is True


def test_penalty_status_ignores_records_outside_window(client, seed_data: dict):
    as_of = datetime(2026, 6, 16, 12, 0, 0)
    _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=31))
    _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=2))
    _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=1))

    with SessionLocal() as session:
        ConfigService(session).list_configs()
        status = ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )

    assert status.violation_count == 2
    assert status.is_penalized is False


def test_penalty_status_query_is_read_only(client, seed_data: dict):
    as_of = datetime(2026, 6, 16, 12, 0, 0)
    reservation_id = _seed_timeout_violation(seed_data, occurred_at=as_of - timedelta(days=1))

    with SessionLocal() as session:
        ConfigService(session).list_configs()
        reservation = session.get(Reservation, reservation_id)
        user = session.get(User, seed_data["users"]["student"])
        before_status = reservation.status
        before_violation_count = session.query(ViolationRecord).count()
        before_user_updated_at = user.updated_at

        ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )
        session.flush()

        assert session.get(Reservation, reservation_id).status == before_status
        assert session.query(ViolationRecord).count() == before_violation_count
        assert session.get(User, seed_data["users"]["student"]).updated_at == before_user_updated_at


def test_manual_block_makes_penalty_status_active_without_creating_violation(client, seed_data: dict):
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        before_violation_count = session.query(ViolationRecord).count()
        block = ViolationService(session).activate_manual_reservation_block(
            seed_data["users"]["student"],
            "Repeated no-show follow-up",
            seed_data["users"]["admin"],
        )

        status = ViolationService(session).get_user_penalty_status(seed_data["users"]["student"])

    assert block.user_id == seed_data["users"]["student"]
    assert status.is_penalized is True
    assert status.restriction_source == "MANUAL_BLOCK"
    assert status.manual_block_id == block.id
    assert status.manual_block_reason == "Repeated no-show follow-up"
    with SessionLocal() as session:
        assert session.query(ViolationRecord).count() == before_violation_count


def test_manual_block_activation_is_idempotent(client, seed_data: dict):
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        service = ViolationService(session)
        first = service.activate_manual_reservation_block(
            seed_data["users"]["student"],
            "First reason",
            seed_data["users"]["admin"],
        )
        second = service.activate_manual_reservation_block(
            seed_data["users"]["student"],
            "Second reason should not create another active block",
            seed_data["users"]["admin"],
        )

    with SessionLocal() as session:
        active_blocks = (
            session.query(UserReservationBlock)
            .filter(
                UserReservationBlock.user_id == seed_data["users"]["student"],
                UserReservationBlock.released_at.is_(None),
            )
            .all()
        )

    assert first.id == second.id
    assert len(active_blocks) == 1
    assert active_blocks[0].reason == "First reason"


def test_manual_block_release_preserves_history_and_removes_manual_source(client, seed_data: dict):
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        service = ViolationService(session)
        block = service.activate_manual_reservation_block(
            seed_data["users"]["student"],
            "Temporary manual block",
            seed_data["users"]["admin"],
        )
        released = service.release_manual_reservation_block(
            seed_data["users"]["student"],
            seed_data["users"]["admin"],
        )
        status = ViolationService(session).get_user_penalty_status(seed_data["users"]["student"])

    assert released.id == block.id
    assert released.released_at is not None
    assert released.released_by_admin_id == seed_data["users"]["admin"]
    assert status.is_penalized is False
    assert status.restriction_source == "NONE"
    with SessionLocal() as session:
        persisted = session.get(UserReservationBlock, block.id)
        assert persisted is not None
        assert persisted.released_at is not None


def test_manual_release_without_active_block_fails(client, seed_data: dict):
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        try:
            ViolationService(session).release_manual_reservation_block(
                seed_data["users"]["student"],
                seed_data["users"]["admin"],
            )
        except Exception as exc:
            assert getattr(exc, "code", None) == "bad_request"
        else:
            raise AssertionError("release should fail without an active manual block")


def test_penalty_status_reports_auto_and_manual_sources_together(client, seed_data: dict):
    as_of = datetime.now().replace(minute=0, second=0, microsecond=0)
    for occurred_at in [as_of - timedelta(days=3), as_of - timedelta(days=2), as_of - timedelta(days=1)]:
        _seed_timeout_violation(seed_data, occurred_at=occurred_at)

    with SessionLocal() as session:
        ConfigService(session).list_configs()
        ViolationService(session).activate_manual_reservation_block(
            seed_data["users"]["student"],
            "Manual block while auto penalty is active",
            seed_data["users"]["admin"],
        )
        status = ViolationService(session).get_user_penalty_status(
            seed_data["users"]["student"],
            as_of=as_of,
        )

    assert status.is_penalized is True
    assert status.restriction_source == "AUTO_AND_MANUAL"
    assert status.penalty_start == as_of - timedelta(days=1)
    assert status.manual_block_id is not None
