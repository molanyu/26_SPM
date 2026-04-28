from __future__ import annotations

from datetime import datetime, time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.core.database import SessionLocal
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.violation.repositories.statistics_repository import StatisticsRepository
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)


def _login_admin(client: TestClient, *, email: str, password: str) -> None:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def _seed_statistics_records(seed_data: dict) -> dict[str, str]:
    target_day = datetime(2026, 4, 15)
    with SessionLocal() as session:
        room_alpha = StudyRoom(
            name="Usage Alpha Room",
            location="Library 201",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(20, 0),
        )
        room_beta = StudyRoom(
            name="Usage Beta Room",
            location="Library 301",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(9, 0),
            close_time=time(17, 0),
        )
        inactive_room = StudyRoom(
            name="Inactive Archive Room",
            location="Library B1",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=False,
            open_time=time(8, 0),
            close_time=time(20, 0),
        )
        session.add_all([room_alpha, room_beta, inactive_room])
        session.flush()

        alpha_seat_1 = Seat(
            room_id=room_alpha.id,
            seat_code="A-01",
            seat_label="Alpha Seat 1",
            is_active=True,
            is_window_side=True,
            has_power_socket=True,
            has_track_socket=False,
        )
        alpha_seat_2 = Seat(
            room_id=room_alpha.id,
            seat_code="A-02",
            seat_label="Alpha Seat 2",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=True,
        )
        beta_seat = Seat(
            room_id=room_beta.id,
            seat_code="B-01",
            seat_label="Beta Seat 1",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        inactive_seat = Seat(
            room_id=inactive_room.id,
            seat_code="X-01",
            seat_label="Inactive Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=False,
            has_track_socket=False,
        )
        session.add_all([alpha_seat_1, alpha_seat_2, beta_seat, inactive_seat])
        session.flush()

        reservations = [
            Reservation(
                user_id=seed_data["users"]["student"],
                seat_id=alpha_seat_1.id,
                room_id=room_alpha.id,
                start_time=target_day.replace(hour=8, minute=0),
                end_time=target_day.replace(hour=10, minute=0),
                status=RESERVATION_STATUS_CHECKED_IN,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            ),
            Reservation(
                user_id=seed_data["users"]["student"],
                seat_id=alpha_seat_2.id,
                room_id=room_alpha.id,
                start_time=target_day.replace(hour=10, minute=0),
                end_time=target_day.replace(hour=12, minute=0),
                status=RESERVATION_STATUS_EXPIRED,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            ),
            Reservation(
                user_id=seed_data["users"]["student"],
                seat_id=alpha_seat_2.id,
                room_id=room_alpha.id,
                start_time=target_day.replace(hour=13, minute=0),
                end_time=target_day.replace(hour=15, minute=0),
                status=RESERVATION_STATUS_CANCELLED,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by="STUDENT",
                cancel_reason="No longer needed.",
            ),
            Reservation(
                user_id=seed_data["users"]["target"],
                seat_id=beta_seat.id,
                room_id=room_beta.id,
                start_time=target_day.replace(hour=9, minute=0),
                end_time=target_day.replace(hour=11, minute=0),
                status=RESERVATION_STATUS_CHECKED_IN,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            ),
            Reservation(
                user_id=seed_data["users"]["target"],
                seat_id=beta_seat.id,
                room_id=room_beta.id,
                start_time=target_day.replace(hour=11, minute=0),
                end_time=target_day.replace(hour=12, minute=0),
                status=RESERVATION_STATUS_BOOKED,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            ),
            Reservation(
                user_id=seed_data["users"]["student"],
                seat_id=inactive_seat.id,
                room_id=inactive_room.id,
                start_time=target_day.replace(hour=14, minute=0),
                end_time=target_day.replace(hour=16, minute=0),
                status=RESERVATION_STATUS_EXPIRED,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            ),
        ]
        session.add_all(reservations)
        session.flush()

        session.add_all(
            [
                ViolationRecord(
                    user_id=seed_data["users"]["student"],
                    reservation_id=reservations[1].id,
                    violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                    occurred_at=target_day.replace(hour=12, minute=20),
                    remark=None,
                ),
                ViolationRecord(
                    user_id=seed_data["users"]["student"],
                    reservation_id=reservations[5].id,
                    violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                    occurred_at=target_day.replace(hour=16, minute=20),
                    remark=None,
                ),
            ],
        )
        session.commit()

    return {
        "date_from": target_day.date().isoformat(),
        "date_to": target_day.date().isoformat(),
    }


def test_admin_can_query_usage_statistics_with_expected_rates(client: TestClient, seed_data: dict):
    params = _seed_statistics_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/statistics/usage", params=params)

    assert response.status_code == 200
    payload = response.json()
    assert payload["date_from"] == params["date_from"]
    assert payload["date_to"] == params["date_to"]
    assert payload["overview"] == {
        "total_reserved_minutes": 420,
        "total_violation_count": 1,
        "overall_violation_rate": 0.3333,
    }
    assert payload["rooms"] == [
        {"room_id": 1, "room_name": "Usage Alpha Room", "usage_rate": 0.1667},
        {"room_id": 2, "room_name": "Usage Beta Room", "usage_rate": 0.375},
    ]
    assert payload["seats"] == [
        {"seat_id": 1, "seat_code": "A-01", "room_id": 1, "usage_rate": 0.1667},
        {"seat_id": 2, "seat_code": "A-02", "room_id": 1, "usage_rate": 0.1667},
        {"seat_id": 3, "seat_code": "B-01", "room_id": 2, "usage_rate": 0.375},
    ]


def test_usage_statistics_returns_zeroed_result_when_no_active_resources(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/statistics/usage",
        params={"date_from": "2026-04-15", "date_to": "2026-04-15"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "date_from": "2026-04-15",
        "date_to": "2026-04-15",
        "overview": {
            "total_reserved_minutes": 0,
            "total_violation_count": 0,
            "overall_violation_rate": 0.0,
        },
        "rooms": [],
        "seats": [],
    }


def test_usage_statistics_rejects_invalid_date_range(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/statistics/usage",
        params={"date_from": "2026-04-16", "date_to": "2026-04-15"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_overlap_duration_expression_compiles_for_postgresql():
    repository = StatisticsRepository(session=None)  # type: ignore[arg-type]
    expression = repository._build_overlap_seconds_expression(
        window_start=datetime(2026, 4, 15, 0, 0),
        window_end=datetime(2026, 4, 16, 0, 0),
    )
    compiled_sql = str(
        select(expression).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        ),
    ).lower()

    assert "extract(epoch from" in compiled_sql
    assert "strftime" not in compiled_sql


def test_unauthenticated_and_limited_admin_cannot_query_usage_statistics(client: TestClient, seed_data: dict):
    _seed_statistics_records(seed_data)

    unauthenticated = client.get(
        "/admin/statistics/usage",
        params={"date_from": "2026-04-15", "date_to": "2026-04-15"},
    )
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["code"] == "unauthenticated"

    _login_admin(
        client,
        email=seed_data["credentials"]["limited_admin_email"],
        password=seed_data["credentials"]["limited_admin_password"],
    )
    forbidden = client.get(
        "/admin/statistics/usage",
        params={"date_from": "2026-04-15", "date_to": "2026-04-15"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"
