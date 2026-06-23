from __future__ import annotations

from datetime import datetime, timedelta, time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.identity.models.user import User
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.system_config.services.config_service import ConfigService
from app.modules.violation.models.violation_record import VIOLATION_TYPE_NO_SHOW_TIMEOUT, ViolationRecord
from app.modules.violation.services.violation_service import ViolationService


def _login_admin(client: TestClient, *, email: str, password: str) -> None:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def _seed_admin_reservation_resources(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        math_student = User(
            student_no="20240002",
            name="Math Student",
            password_hash=hash_password("math-student-pass"),
            department_id=seed_data["departments"]["math"],
            is_active=True,
        )
        session.add(math_student)
        session.flush()

        cs_room = StudyRoom(
            name="Admin CS Room",
            location="Engineering 301",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        math_room = StudyRoom(
            name="Admin Math Room",
            location="Science 301",
            department_id=seed_data["departments"]["math"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add_all([cs_room, math_room])
        session.flush()

        cs_seat = Seat(
            room_id=cs_room.id,
            seat_code="D-01",
            seat_label="Admin CS Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        math_seat = Seat(
            room_id=math_room.id,
            seat_code="E-01",
            seat_label="Admin Math Seat",
            is_active=True,
            is_window_side=True,
            has_power_socket=True,
            has_track_socket=True,
        )
        math_second_seat = Seat(
            room_id=math_room.id,
            seat_code="E-02",
            seat_label="Admin Math Second Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add_all([cs_seat, math_seat, math_second_seat])
        session.commit()

        return {
            "math_student": math_student.id,
            "cs_room": cs_room.id,
            "math_room": math_room.id,
            "cs_seat": cs_seat.id,
            "math_seat": math_seat.id,
            "math_second_seat": math_second_seat.id,
        }


def _future_slot(
    *,
    days: int = 1,
    start_hour: int = 10,
    start_minute: int = 0,
    duration_hours: int = 2,
) -> tuple[datetime, datetime]:
    base = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=days)
    start = base.replace(hour=start_hour, minute=start_minute)
    end = start + timedelta(hours=duration_hours)
    return start, end


def _insert_reservation(
    *,
    user_id: int,
    seat_id: int,
    room_id: int,
    start_time: datetime,
    end_time: datetime,
) -> int:
    with SessionLocal() as session:
        reservation = Reservation(
            user_id=user_id,
            seat_id=seat_id,
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.commit()
        return reservation.id


def _seed_active_penalty_records(*, user_id: int, room_id: int, seat_id: int) -> None:
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    occurred_times = [
        now - timedelta(days=3),
        now - timedelta(days=2),
        now - timedelta(days=1),
    ]
    with SessionLocal() as session:
        for index, occurred_at in enumerate(occurred_times):
            reservation = Reservation(
                user_id=user_id,
                seat_id=seat_id,
                room_id=room_id,
                start_time=occurred_at - timedelta(hours=2),
                end_time=occurred_at - timedelta(hours=1),
                status=RESERVATION_STATUS_EXPIRED,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            )
            session.add(reservation)
            session.flush()
            session.add(
                ViolationRecord(
                    user_id=user_id,
                    reservation_id=reservation.id,
                    violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                    occurred_at=occurred_at,
                    remark=f"Admin penalty seed {index}",
                ),
            )
        session.commit()


def test_admin_can_create_reservation_for_target_student(client: TestClient, seed_data: dict):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "BOOKED"
    assert payload["data"]["user_id"] == resource_ids["math_student"]
    assert payload["data"]["room_id"] == resource_ids["math_room"]
    assert payload["data"]["created_by"] == "ADMIN"


def test_admin_can_create_half_hour_reservation_for_target_student(client: TestClient, seed_data: dict):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    start_time, end_time = _future_slot(start_hour=9, start_minute=30, duration_hours=1)

    response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "BOOKED"
    assert payload["start_time"] == start_time.isoformat()
    assert payload["end_time"] == end_time.isoformat()


def test_admin_create_reservation_rejects_invalid_request_scenarios(client: TestClient, seed_data: dict):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    non_half_hour_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": start_time.replace(minute=15).isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert non_half_hour_response.status_code == 400
    assert non_half_hour_response.json()["code"] == "bad_request"

    past_start = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    past_time_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": past_start.isoformat(),
            "end_time": (past_start + timedelta(hours=1)).isoformat(),
        },
    )
    assert past_time_response.status_code == 400
    assert past_time_response.json()["code"] == "bad_request"

    over_max_hours_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=5)).isoformat(),
        },
    )
    assert over_max_hours_response.status_code == 400
    assert over_max_hours_response.json()["code"] == "bad_request"

    invisible_resource_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert invisible_resource_response.status_code == 403
    assert invisible_resource_response.json()["code"] == "forbidden"

    first_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert first_response.status_code == 200

    conflict_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": (start_time + timedelta(hours=1)).isoformat(),
            "end_time": (end_time + timedelta(hours=1)).isoformat(),
        },
    )
    assert conflict_response.status_code == 409
    assert conflict_response.json()["code"] == "conflict"


def test_admin_create_reservation_rejects_penalized_target_before_write(
    client: TestClient,
    seed_data: dict,
):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    _seed_active_penalty_records(
        user_id=resource_ids["math_student"],
        room_id=resource_ids["math_room"],
        seat_id=resource_ids["math_seat"],
    )
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)
    with SessionLocal() as session:
        before_count = session.query(Reservation).count()

    response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_second_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"
    with SessionLocal() as session:
        assert session.query(Reservation).count() == before_count


def test_admin_create_reservation_rejects_manually_blocked_target_before_write(
    client: TestClient,
    seed_data: dict,
):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    with SessionLocal() as session:
        ViolationService(session).activate_manual_reservation_block(
            resource_ids["math_student"],
            "Manual block before admin reservation",
            seed_data["users"]["admin"],
        )
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)
    with SessionLocal() as session:
        before_count = session.query(Reservation).count()

    response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_second_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"
    with SessionLocal() as session:
        assert session.query(Reservation).count() == before_count


def test_admin_create_reservation_rejects_same_user_overlap_on_different_seat(
    client: TestClient,
    seed_data: dict,
):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    first_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_second_seat"],
            "start_time": (start_time + timedelta(minutes=30)).isoformat(),
            "end_time": (end_time + timedelta(minutes=30)).isoformat(),
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["code"] == "conflict"


def test_admin_can_cancel_reservation(client: TestClient, seed_data: dict):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    start_time, end_time = _future_slot(start_hour=14, duration_hours=1)
    reservation_id = _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["cs_seat"],
        room_id=resource_ids["cs_room"],
        start_time=start_time,
        end_time=end_time,
    )

    response = client.post(
        f"/admin/reservations/{reservation_id}/cancel",
        json={"reason": "Admin override"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "CANCELLED"
    assert payload["data"]["cancelled_by"] == "ADMIN"
    assert payload["data"]["cancel_reason"] == "Admin override"


def test_admin_can_query_reservation_records_with_filters(client: TestClient, seed_data: dict):
    resource_ids = _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    first_start, first_end = _future_slot(days=2, start_hour=10, duration_hours=2)
    second_start, second_end = _future_slot(days=3, start_hour=14, duration_hours=1)

    booked_response = client.post(
        "/admin/reservations",
        json={
            "user_id": seed_data["users"]["student"],
            "seat_id": resource_ids["cs_seat"],
            "start_time": first_start.isoformat(),
            "end_time": first_end.isoformat(),
        },
    )
    assert booked_response.status_code == 200
    booked_id = booked_response.json()["data"]["reservation_id"]

    cancelled_response = client.post(
        "/admin/reservations",
        json={
            "user_id": resource_ids["math_student"],
            "seat_id": resource_ids["math_seat"],
            "start_time": second_start.isoformat(),
            "end_time": second_end.isoformat(),
        },
    )
    assert cancelled_response.status_code == 200
    cancelled_id = cancelled_response.json()["data"]["reservation_id"]

    cancel_action = client.post(
        f"/admin/reservations/{cancelled_id}/cancel",
        json={"reason": "Record filter seed"},
    )
    assert cancel_action.status_code == 200

    by_user = client.get("/admin/reservations", params={"user_id": seed_data["users"]["student"]})
    assert by_user.status_code == 200
    assert all(item["user_id"] == seed_data["users"]["student"] for item in by_user.json()["items"])

    by_room = client.get("/admin/reservations", params={"room_id": resource_ids["math_room"]})
    assert by_room.status_code == 200
    assert [item["reservation_id"] for item in by_room.json()["items"]] == [cancelled_id]

    by_seat = client.get("/admin/reservations", params={"seat_id": resource_ids["cs_seat"]})
    assert by_seat.status_code == 200
    assert any(item["reservation_id"] == booked_id for item in by_seat.json()["items"])

    by_status = client.get("/admin/reservations", params={"status": "CANCELLED"})
    assert by_status.status_code == 200
    assert [item["reservation_id"] for item in by_status.json()["items"]] == [cancelled_id]

    by_date = client.get(
        "/admin/reservations",
        params={
            "date_from": first_start.date().isoformat(),
            "date_to": first_start.date().isoformat(),
        },
    )
    assert by_date.status_code == 200
    assert [item["reservation_id"] for item in by_date.json()["items"]] == [booked_id]


def test_admin_reservation_query_rejects_invalid_status(client: TestClient, seed_data: dict) -> None:
    _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/reservations", params={"status": "INVALID"})

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "bad_request"
    assert payload["message"]


def test_admin_reservation_query_rejects_invalid_date_range(client: TestClient, seed_data: dict) -> None:
    _seed_admin_reservation_resources(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/reservations",
        params={"date_from": "2026-04-20", "date_to": "2026-04-19"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "bad_request"
    assert "date_from" in payload["message"]
