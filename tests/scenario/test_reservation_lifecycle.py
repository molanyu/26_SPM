from __future__ import annotations

from datetime import datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.checkin.models.checkin_record import CheckinRecord
from app.modules.checkin.schemas.checkin import StudentCodeCheckinRequest
from app.modules.checkin.services.checkin_service import CheckinService
from app.modules.checkin.services.code_service import CodeService
from app.modules.checkin.tasks.timeout_release_task import release_expired_reservations
from app.modules.identity.models.user import User
from app.modules.notification.models.notification_log import (
    NOTIFICATION_TYPE_NO_SHOW_REMINDER,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
    NotificationLog,
)
from app.modules.notification.tasks.no_show_reminder_task import send_no_show_reminders
from app.modules.notification.tasks.reservation_reminder_task import send_reservation_reminders
from app.modules.reservation.models.reservation import Reservation
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)


SCENARIO_DAY = datetime(2026, 4, 15)


def _login_student(client: TestClient, seed_data: dict) -> dict[str, str]:
    response = client.post(
        "/student/auth/login",
        json={
            "student_no": seed_data["credentials"]["student_no"],
            "password": seed_data["credentials"]["student_password"],
        },
    )
    assert response.status_code == 200, "student login failed"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _login_admin(client: TestClient, seed_data: dict) -> None:
    response = client.post(
        "/admin/auth/login",
        json={
            "email": seed_data["credentials"]["admin_email"],
            "password": seed_data["credentials"]["admin_password"],
        },
    )
    assert response.status_code == 200, "admin login failed"


def _seed_scenario_resources(seed_data: dict, *, suffix: str) -> dict[str, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name=f"Scenario Room {suffix}",
            location=f"Scenario Building {suffix}",
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
            seat_code=f"SCN-{suffix}-01",
            seat_label=f"Scenario Seat {suffix}",
            is_active=True,
            is_window_side=True,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.commit()
        return {
            "room_id": room.id,
            "seat_id": seat.id,
        }


def _create_student_reservation(
    client: TestClient,
    *,
    headers: dict[str, str],
    seat_id: int,
    start_time: datetime,
    end_time: datetime,
    stage: str,
) -> int:
    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": seat_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert response.status_code == 200, f"{stage}: reservation creation failed: {response.text}"
    payload = response.json()["data"]
    assert payload["status"] == "BOOKED", f"{stage}: reservation was not created as BOOKED"
    assert payload["seat_id"] == seat_id, f"{stage}: reservation points to the wrong seat"
    return int(payload["reservation_id"])


def _get_notification_count(reservation_id: int, notification_type: str) -> int:
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


def _get_violation_count(reservation_id: int) -> int:
    with SessionLocal() as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(ViolationRecord)
                .where(
                    ViolationRecord.reservation_id == reservation_id,
                    ViolationRecord.violation_type == VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                ),
            )
            or 0,
        )


def _get_reservation_status(reservation_id: int) -> str:
    with SessionLocal() as session:
        reservation = session.get(Reservation, reservation_id)
        assert reservation is not None, "reservation lookup failed"
        return reservation.status


def _assert_admin_reservation_status(
    client: TestClient,
    *,
    reservation_id: int,
    expected_status: str,
    stage: str,
) -> None:
    response = client.get("/admin/reservations", params={"status": expected_status})
    assert response.status_code == 200, f"{stage}: admin reservation query failed: {response.text}"
    matching = [item for item in response.json()["items"] if item["reservation_id"] == reservation_id]
    assert matching, f"{stage}: reservation {reservation_id} not visible in admin records"
    assert matching[0]["status"] == expected_status, f"{stage}: admin record has wrong status"


def test_scn_01_normal_reservation_lifecycle(client: TestClient, seed_data: dict) -> None:
    resource_ids = _seed_scenario_resources(seed_data, suffix="01")
    student_headers = _login_student(client, seed_data)
    _login_admin(client, seed_data)
    start_time = SCENARIO_DAY.replace(hour=10, minute=0)
    end_time = start_time + timedelta(hours=2)

    rooms_response = client.get("/student/rooms", headers=student_headers)
    assert rooms_response.status_code == 200, "SCN-01 room query failed"
    assert any(
        item["id"] == resource_ids["room_id"] for item in rooms_response.json()["items"]
    ), "SCN-01 target room was not visible to the student"

    seats_response = client.get(
        f"/student/rooms/{resource_ids['room_id']}/seats",
        headers=student_headers,
        params={
            "date": start_time.date().isoformat(),
            "start_time": start_time.time().isoformat(),
            "end_time": end_time.time().isoformat(),
        },
    )
    assert seats_response.status_code == 200, "SCN-01 seat query failed"
    assert any(
        item["seat_id"] == resource_ids["seat_id"] and item["status"] == "AVAILABLE"
        for item in seats_response.json()["items"]
    ), "SCN-01 target seat was not visible as available before reservation"

    reservation_id = _create_student_reservation(
        client,
        headers=student_headers,
        seat_id=resource_ids["seat_id"],
        start_time=start_time,
        end_time=end_time,
        stage="SCN-01 create reservation",
    )

    reminder_now = start_time - timedelta(minutes=15)
    with SessionLocal() as session:
        first_reminder = send_reservation_reminders(session, now=reminder_now)
    with SessionLocal() as session:
        second_reminder = send_reservation_reminders(session, now=reminder_now)
    assert first_reminder.sent_reservation_ids == [
        reservation_id,
    ], "SCN-01 reservation reminder did not target the created reservation"
    assert second_reminder.sent_reservation_ids == [], "SCN-01 reservation reminder was not idempotent"
    assert (
        _get_notification_count(reservation_id, NOTIFICATION_TYPE_RESERVATION_REMINDER) == 1
    ), "SCN-01 reservation reminder log count is not idempotent"

    checkin_now = start_time + timedelta(minutes=5)
    with SessionLocal() as session:
        code = CodeService(session, settings=client.app.state.settings).ensure_daily_code(
            resource_ids["room_id"],
            code_date=start_time.date(),
            now=reminder_now,
        )
    with SessionLocal() as session:
        student = session.get(User, seed_data["users"]["student"])
        assert student is not None, "SCN-01 student fixture lookup failed"
        checkin_result = CheckinService(session, settings=client.app.state.settings).check_in_by_code(
            student,
            StudentCodeCheckinRequest(reservation_id=reservation_id, code=code.code),
            now=checkin_now,
        )
    assert checkin_result.status == "CHECKED_IN", "SCN-01 check-in did not return CHECKED_IN"
    assert _get_reservation_status(reservation_id) == "CHECKED_IN", "SCN-01 reservation status was not CHECKED_IN"

    with SessionLocal() as session:
        checkin_records = session.scalar(
            select(func.count())
            .select_from(CheckinRecord)
            .where(CheckinRecord.reservation_id == reservation_id),
        )
    assert checkin_records == 1, "SCN-01 check-in did not persist exactly one record"

    _assert_admin_reservation_status(
        client,
        reservation_id=reservation_id,
        expected_status="CHECKED_IN",
        stage="SCN-01 admin reservation records",
    )

    statistics_response = client.get(
        "/admin/statistics/usage",
        params={
            "date_from": start_time.date().isoformat(),
            "date_to": start_time.date().isoformat(),
        },
    )
    assert statistics_response.status_code == 200, f"SCN-01 usage statistics failed: {statistics_response.text}"
    overview = statistics_response.json()["overview"]
    assert overview["total_reserved_minutes"] == 120, "SCN-01 usage statistics did not include checked-in duration"
    assert overview["total_violation_count"] == 0, "SCN-01 usage statistics unexpectedly counted a violation"


def test_scn_02_no_show_violation_and_seat_release_lifecycle(client: TestClient, seed_data: dict) -> None:
    resource_ids = _seed_scenario_resources(seed_data, suffix="02")
    student_headers = _login_student(client, seed_data)
    _login_admin(client, seed_data)
    start_time = SCENARIO_DAY.replace(hour=14, minute=0)
    end_time = start_time + timedelta(hours=2)

    reservation_id = _create_student_reservation(
        client,
        headers=student_headers,
        seat_id=resource_ids["seat_id"],
        start_time=start_time,
        end_time=end_time,
        stage="SCN-02 create reservation",
    )

    conflicting_response = client.post(
        "/student/reservations",
        headers=student_headers,
        json={
            "seat_id": resource_ids["seat_id"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert conflicting_response.status_code == 409, "SCN-02 seat was not occupied before timeout release"

    no_show_now = start_time + timedelta(minutes=10)
    with SessionLocal() as session:
        first_no_show = send_no_show_reminders(session, now=no_show_now)
    with SessionLocal() as session:
        second_no_show = send_no_show_reminders(session, now=no_show_now)
    assert first_no_show.sent_reservation_ids == [
        reservation_id,
    ], "SCN-02 no-show reminder did not target the created reservation"
    assert second_no_show.sent_reservation_ids == [], "SCN-02 no-show reminder was not idempotent"
    assert (
        _get_notification_count(reservation_id, NOTIFICATION_TYPE_NO_SHOW_REMINDER) == 1
    ), "SCN-02 no-show reminder log count is not idempotent"

    release_now = start_time + timedelta(minutes=15)
    with SessionLocal() as session:
        first_release = release_expired_reservations(session, now=release_now)
    with SessionLocal() as session:
        second_release = release_expired_reservations(session, now=release_now)
    assert first_release.expired_reservation_ids == [
        reservation_id,
    ], "SCN-02 timeout release did not expire the created reservation"
    assert second_release.expired_reservation_ids == [], "SCN-02 timeout release was not idempotent"
    assert _get_reservation_status(reservation_id) == "EXPIRED", "SCN-02 reservation status was not EXPIRED"
    assert _get_violation_count(reservation_id) == 1, "SCN-02 timeout violation count is not idempotent"

    _assert_admin_reservation_status(
        client,
        reservation_id=reservation_id,
        expected_status="EXPIRED",
        stage="SCN-02 admin reservation records",
    )

    violations_response = client.get("/admin/violations", params={"user_id": seed_data["users"]["student"]})
    assert violations_response.status_code == 200, f"SCN-02 admin violation query failed: {violations_response.text}"
    matching_violations = [
        item for item in violations_response.json()["items"] if item["reservation_id"] == reservation_id
    ]
    assert matching_violations, "SCN-02 violation was not visible in admin violation records"
    assert (
        matching_violations[0]["violation_type"] == VIOLATION_TYPE_NO_SHOW_TIMEOUT
    ), "SCN-02 admin violation record has wrong type"

    seats_response = client.get(
        f"/student/rooms/{resource_ids['room_id']}/seats",
        headers=student_headers,
        params={
            "date": start_time.date().isoformat(),
            "start_time": start_time.time().isoformat(),
            "end_time": end_time.time().isoformat(),
        },
    )
    assert seats_response.status_code == 200, "SCN-02 seat query after timeout release failed"
    assert any(
        item["seat_id"] == resource_ids["seat_id"] and item["status"] == "AVAILABLE"
        for item in seats_response.json()["items"]
    ), "SCN-02 released seat was not visible as available"

    replacement_id = _create_student_reservation(
        client,
        headers=student_headers,
        seat_id=resource_ids["seat_id"],
        start_time=start_time,
        end_time=end_time,
        stage="SCN-02 create replacement reservation after release",
    )
    assert replacement_id != reservation_id, "SCN-02 replacement reservation reused the expired reservation id"
