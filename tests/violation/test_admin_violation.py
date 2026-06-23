from __future__ import annotations

from datetime import datetime, timedelta, time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.identity.models.user_role import UserRole
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)
from app.modules.violation.models.user_reservation_block import UserReservationBlock


def _login_admin(client: TestClient, *, email: str, password: str) -> None:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def _seed_violation_records(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        cs_room = StudyRoom(
            name="Violation Query CS Room",
            location="Engineering 801",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        math_room = StudyRoom(
            name="Violation Query Math Room",
            location="Science 801",
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
            seat_code="VQ-01",
            seat_label="Violation Query Seat 1",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        math_seat = Seat(
            room_id=math_room.id,
            seat_code="VQ-02",
            seat_label="Violation Query Seat 2",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=True,
        )
        session.add_all([cs_seat, math_seat])
        session.flush()

        now = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        first_reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=cs_seat.id,
            room_id=cs_room.id,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status=RESERVATION_STATUS_EXPIRED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        second_reservation = Reservation(
            user_id=seed_data["users"]["target"],
            seat_id=math_seat.id,
            room_id=math_room.id,
            start_time=now - timedelta(days=1, hours=2),
            end_time=now - timedelta(days=1, hours=1),
            status=RESERVATION_STATUS_EXPIRED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add_all([first_reservation, second_reservation])
        session.flush()

        session.add_all(
            [
                ViolationRecord(
                    user_id=seed_data["users"]["student"],
                    reservation_id=first_reservation.id,
                    violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                    occurred_at=now,
                    remark=None,
                ),
                ViolationRecord(
                    user_id=seed_data["users"]["target"],
                    reservation_id=second_reservation.id,
                    violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                    occurred_at=now - timedelta(days=1),
                    remark=None,
                ),
            ],
        )
        session.commit()
        return {
            "student_user": seed_data["users"]["student"],
            "student_no": seed_data["credentials"]["student_no"],
            "target_user": seed_data["users"]["target"],
            "cs_room": cs_room.id,
            "math_room": math_room.id,
        }


def test_admin_can_query_violations_with_supported_filters(client: TestClient, seed_data: dict):
    resource_ids = _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/violations")
    assert response.status_code == 200
    assert response.json()["total"] == 2

    student_no_filtered = client.get(
        "/admin/violations",
        params={"student_no": resource_ids["student_no"]},
    )
    assert student_no_filtered.status_code == 200
    student_no_items = student_no_filtered.json()["items"]
    assert len(student_no_items) == 1
    assert student_no_items[0]["student_no"] == resource_ids["student_no"]

    user_filtered = client.get(
        "/admin/violations",
        params={"user_id": resource_ids["student_user"]},
    )
    assert user_filtered.status_code == 200
    user_items = user_filtered.json()["items"]
    assert len(user_items) == 1
    assert user_items[0]["user_id"] == resource_ids["student_user"]

    room_filtered = client.get(
        "/admin/violations",
        params={"room_id": resource_ids["math_room"]},
    )
    assert room_filtered.status_code == 200
    room_items = room_filtered.json()["items"]
    assert len(room_items) == 1
    assert room_items[0]["room_id"] == resource_ids["math_room"]

    today = datetime.now().date().isoformat()
    today_filtered = client.get(
        "/admin/violations",
        params={"date_from": today, "date_to": today},
    )
    assert today_filtered.status_code == 200
    today_items = today_filtered.json()["items"]
    assert len(today_items) == 1
    assert today_items[0]["room_id"] == resource_ids["cs_room"]


def test_admin_violation_query_returns_single_user_summary(client: TestClient, seed_data: dict):
    resource_ids = _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/violations", params={"user_id": resource_ids["student_user"]})

    assert response.status_code == 200
    summary = response.json()["user_summary"]
    assert summary["user_id"] == resource_ids["student_user"]
    assert summary["student_no"] == resource_ids["student_no"]
    assert summary["violation_count"] == 1
    assert summary["is_penalized"] is False
    assert summary["restriction_source"] == "NONE"


def test_manual_block_endpoints_activate_and_release_with_write_permission(
    client: TestClient,
    seed_data: dict,
):
    _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    activate = client.post(
        f"/admin/violations/users/{seed_data['users']['student']}/manual-block",
        json={"reason": "Manual block from admin API"},
    )

    assert activate.status_code == 200
    activate_payload = activate.json()
    assert activate_payload["success"] is True
    assert activate_payload["data"]["is_penalized"] is True
    assert activate_payload["data"]["restriction_source"] == "MANUAL_BLOCK"
    block_id = activate_payload["data"]["manual_block_id"]
    with SessionLocal() as session:
        assert session.get(UserReservationBlock, block_id) is not None
        assert session.query(ViolationRecord).count() == 2

    duplicate = client.post(
        f"/admin/violations/users/{seed_data['users']['student']}/manual-block",
        json={"reason": "Second request should be idempotent"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["manual_block_id"] == block_id

    release = client.post(f"/admin/violations/users/{seed_data['users']['student']}/manual-block/release")

    assert release.status_code == 200
    release_payload = release.json()
    assert release_payload["data"]["manual_block_id"] == block_id
    assert release_payload["data"]["released_at"] is not None
    with SessionLocal() as session:
        persisted = session.get(UserReservationBlock, block_id)
        assert persisted is not None
        assert persisted.released_at is not None


def test_unauthenticated_and_limited_admin_cannot_query_violations(client: TestClient, seed_data: dict):
    _seed_violation_records(seed_data)

    unauthenticated = client.get("/admin/violations")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["code"] == "unauthenticated"

    _login_admin(
        client,
        email=seed_data["credentials"]["limited_admin_email"],
        password=seed_data["credentials"]["limited_admin_password"],
    )
    forbidden = client.get("/admin/violations")
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"


def test_manual_block_write_permission_is_not_required_for_get_but_is_required_for_post(
    client: TestClient,
    seed_data: dict,
):
    with SessionLocal() as session:
        session.add(UserRole(user_id=seed_data["users"]["target"], role_id=seed_data["roles"]["viewer"]))
        session.commit()
    _login_admin(
        client,
        email=seed_data["credentials"]["target_email"],
        password=seed_data["credentials"]["target_password"],
    )

    get_response = client.get("/admin/violations")
    assert get_response.status_code == 200

    post_response = client.post(
        f"/admin/violations/users/{seed_data['users']['student']}/manual-block",
        json={"reason": "Should be forbidden"},
    )
    assert post_response.status_code == 403
    assert post_response.json()["code"] == "forbidden"
