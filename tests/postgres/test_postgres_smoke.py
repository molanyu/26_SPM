from __future__ import annotations

import os
from datetime import datetime, timedelta, time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import create_app
from app.modules.identity.models.department import Department
from app.modules.identity.models.user import User
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom

POSTGRES_REGRESSION_URL = os.getenv("POSTGRES_REGRESSION_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_REGRESSION_URL,
    reason="POSTGRES_REGRESSION_URL is required for PostgreSQL regression tests.",
)


@pytest.fixture
def postgres_client() -> TestClient:
    settings = Settings(
        database_url=POSTGRES_REGRESSION_URL,
        database_auto_create=False,
        jwt_secret_key="postgres-smoke-secret",
        admin_session_cookie_name="pg_smoke_admin_session",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def _seed_student_chain() -> dict[str, str | int]:
    unique_suffix = uuid4().hex[:8]
    with SessionLocal() as session:
        department = Department(
            name=f"Postgres Department {unique_suffix}",
            code=f"PG{unique_suffix}".upper(),
            is_active=True,
        )
        session.add(department)
        session.flush()

        student = User(
            student_no=f"PG{unique_suffix}",
            name="Postgres Student",
            password_hash=hash_password("student-pass"),
            department_id=department.id,
            is_active=True,
        )
        session.add(student)
        session.flush()

        room = StudyRoom(
            name=f"Postgres Room {unique_suffix}",
            location="Building A 301",
            department_id=department.id,
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        seat = Seat(
            room_id=room.id,
            seat_code=f"A-{unique_suffix[:4]}",
            seat_label="Postgres Seat",
            is_active=True,
            is_window_side=True,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.commit()

        return {
            "student_no": student.student_no,
            "password": "student-pass",
            "room_id": room.id,
            "seat_id": seat.id,
        }


def test_postgres_migrated_app_supports_student_reservation_flow(postgres_client: TestClient) -> None:
    seed = _seed_student_chain()

    health_response = postgres_client.get("/health")
    assert health_response.status_code == 200

    login_response = postgres_client.post(
        "/student/auth/login",
        json={
            "student_no": seed["student_no"],
            "password": seed["password"],
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rooms_response = postgres_client.get("/student/rooms?page=1&page_size=20", headers=headers)
    assert rooms_response.status_code == 200
    assert any(item["id"] == seed["room_id"] for item in rooms_response.json()["items"])

    reservation_day = datetime.now().date() + timedelta(days=1)
    current_hour = datetime.combine(reservation_day, time(10, 0))
    reservation_response = postgres_client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": seed["seat_id"],
            "start_time": current_hour.isoformat(),
            "end_time": (current_hour + timedelta(hours=2)).isoformat(),
        },
    )
    assert reservation_response.status_code == 200
    reservation_id = reservation_response.json()["data"]["reservation_id"]

    current_response = postgres_client.get("/student/reservations/current", headers=headers)
    assert current_response.status_code == 200
    assert any(item["reservation_id"] == reservation_id for item in current_response.json()["items"])
