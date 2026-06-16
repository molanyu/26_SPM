from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime, time, timedelta

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


def _login_student(client: TestClient, *, student_no: str, password: str) -> dict[str, str]:
    response = client.post(
        "/student/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_resource_data(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        public_room = StudyRoom(
            name="Public Room",
            location="Library 201",
            department_id=None,
            is_department_only=False,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        cs_room = StudyRoom(
            name="CS Room",
            location="Engineering 301",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(9, 0),
            close_time=time(21, 0),
        )
        math_room = StudyRoom(
            name="Math Room",
            location="Science 401",
            department_id=seed_data["departments"]["math"],
            is_department_only=True,
            is_active=True,
            open_time=time(9, 30),
            close_time=time(20, 30),
        )
        inactive_room = StudyRoom(
            name="Inactive Room",
            location="Old Building",
            department_id=None,
            is_department_only=False,
            is_active=False,
            open_time=time(10, 0),
            close_time=time(18, 0),
        )
        session.add_all([public_room, cs_room, math_room, inactive_room])
        session.flush()

        seats = [
            Seat(
                room_id=cs_room.id,
                seat_code="A-01",
                seat_label="Window Power Seat",
                is_active=True,
                is_window_side=True,
                has_power_socket=True,
                has_track_socket=False,
            ),
            Seat(
                room_id=cs_room.id,
                seat_code="A-02",
                seat_label="Track Seat",
                is_active=True,
                is_window_side=False,
                has_power_socket=False,
                has_track_socket=True,
            ),
            Seat(
                room_id=cs_room.id,
                seat_code="A-03",
                seat_label="Inactive Seat",
                is_active=False,
                is_window_side=True,
                has_power_socket=True,
                has_track_socket=True,
            ),
        ]
        session.add_all(seats)
        session.commit()

        return {
            "public_room": public_room.id,
            "cs_room": cs_room.id,
            "math_room": math_room.id,
            "inactive_room": inactive_room.id,
            "window_power_seat": seats[0].id,
        }


def test_student_rooms_visibility_filters_by_department_and_active(client: TestClient, seed_data: dict):
    room_ids = _seed_resource_data(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    response = client.get("/student/rooms", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    returned_ids = {item["id"] for item in payload["items"]}
    assert room_ids["public_room"] in returned_ids
    assert room_ids["cs_room"] in returned_ids
    assert room_ids["math_room"] not in returned_ids
    assert room_ids["inactive_room"] not in returned_ids


def test_student_can_filter_room_seats_by_resource_attributes_and_status(client: TestClient, seed_data: dict):
    room_ids = _seed_resource_data(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    response = client.get(
        f"/student/rooms/{room_ids['cs_room']}/seats",
        headers=headers,
        params={"is_window_side": "true", "has_power_socket": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    seat = payload["items"][0]
    assert seat["seat_code"] == "A-01"
    assert seat["status"] == "AVAILABLE"
    assert seat["is_window_side"] is True
    assert seat["has_power_socket"] is True
    assert seat["has_track_socket"] is False


def test_student_can_filter_room_seats_by_track_socket(client: TestClient, seed_data: dict):
    room_ids = _seed_resource_data(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    track_enabled_response = client.get(
        f"/student/rooms/{room_ids['cs_room']}/seats",
        headers=headers,
        params={"has_track_socket": "true"},
    )
    assert track_enabled_response.status_code == 200
    track_enabled_codes = {item["seat_code"] for item in track_enabled_response.json()["items"]}
    assert track_enabled_codes == {"A-02"}

    track_disabled_response = client.get(
        f"/student/rooms/{room_ids['cs_room']}/seats",
        headers=headers,
        params={"has_track_socket": "false"},
    )
    assert track_disabled_response.status_code == 200
    track_disabled_codes = {item["seat_code"] for item in track_disabled_response.json()["items"]}
    assert track_disabled_codes == {"A-01"}


def test_student_room_seats_keep_resource_side_status_when_reservation_exists(
    client: TestClient,
    seed_data: dict,
):
    room_ids = _seed_resource_data(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time = datetime.combine(dt_date.today() + timedelta(days=1), time(10, 0))
    end_time = start_time + timedelta(hours=2)
    with SessionLocal() as session:
        session.add(
            Reservation(
                user_id=seed_data["users"]["target"],
                seat_id=room_ids["window_power_seat"],
                room_id=room_ids["cs_room"],
                start_time=start_time,
                end_time=end_time,
                status=RESERVATION_STATUS_BOOKED,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            ),
        )
        session.commit()

    response = client.get(
        f"/student/rooms/{room_ids['cs_room']}/seats",
        headers=headers,
        params={
            "date": start_time.date().isoformat(),
            "start_time": start_time.time().isoformat(),
            "end_time": end_time.time().isoformat(),
        },
    )

    assert response.status_code == 200
    seats_by_id = {item["seat_id"]: item for item in response.json()["items"]}
    assert seats_by_id[room_ids["window_power_seat"]]["status"] == "AVAILABLE"


def test_student_cannot_access_other_department_room_seats(client: TestClient, seed_data: dict):
    room_ids = _seed_resource_data(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    response = client.get(f"/student/rooms/{room_ids['math_room']}/seats", headers=headers)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
