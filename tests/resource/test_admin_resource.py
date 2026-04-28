from __future__ import annotations

from datetime import time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


def _login_admin(client: TestClient, *, email: str, password: str) -> None:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def _seed_room(seed_data: dict) -> int:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Seed Room",
            location="Library 101",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(20, 0),
        )
        session.add(room)
        session.commit()
        return room.id


def _seed_room_with_seat(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Seat Room",
            location="Building A",
            department_id=None,
            is_department_only=False,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        seat = Seat(
            room_id=room.id,
            seat_code="B-01",
            seat_label="Seed Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.commit()
        return {"room_id": room.id, "seat_id": seat.id}


def test_admin_can_create_update_list_and_deactivate_room(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    create_response = client.post(
        "/admin/rooms",
        json={
            "name": "Innovation Room",
            "location": "Building B",
            "department_id": seed_data["departments"]["cs"],
            "is_department_only": True,
            "is_active": True,
            "open_time": "08:00:00",
            "close_time": "21:00:00",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()["data"]
    room_id = created["id"]
    assert created["name"] == "Innovation Room"

    list_response = client.get("/admin/rooms")
    assert list_response.status_code == 200
    assert any(item["id"] == room_id for item in list_response.json()["items"])

    update_response = client.put(
        f"/admin/rooms/{room_id}",
        json={
            "name": "Innovation Room Updated",
            "location": "Building C",
            "department_id": None,
            "is_department_only": False,
            "is_active": True,
            "open_time": "09:00:00",
            "close_time": "22:00:00",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Innovation Room Updated"

    deactivate_response = client.post(f"/admin/rooms/{room_id}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["data"]["is_active"] is False


def test_admin_room_api_rejects_invalid_department_on_create_and_update(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    create_invalid_response = client.post(
        "/admin/rooms",
        json={
            "name": "Invalid Department Room",
            "location": "Building D",
            "department_id": 999999,
            "is_department_only": True,
            "is_active": True,
            "open_time": "08:00:00",
            "close_time": "21:00:00",
        },
    )

    assert create_invalid_response.status_code == 400
    assert create_invalid_response.json()["code"] == "bad_request"
    assert "所选院系不存在或已停用，请重新选择。" in create_invalid_response.json()["message"]

    create_valid_response = client.post(
        "/admin/rooms",
        json={
            "name": "Valid Department Room",
            "location": "Building E",
            "department_id": seed_data["departments"]["cs"],
            "is_department_only": True,
            "is_active": True,
            "open_time": "08:00:00",
            "close_time": "21:00:00",
        },
    )
    assert create_valid_response.status_code == 200
    room_id = create_valid_response.json()["data"]["id"]

    update_invalid_response = client.put(
        f"/admin/rooms/{room_id}",
        json={
            "name": "Valid Department Room Updated",
            "location": "Building F",
            "department_id": 999999,
            "is_department_only": True,
            "is_active": True,
            "open_time": "09:00:00",
            "close_time": "22:00:00",
        },
    )

    assert update_invalid_response.status_code == 400
    assert update_invalid_response.json()["code"] == "bad_request"
    assert "所选院系不存在或已停用，请重新选择。" in update_invalid_response.json()["message"]


def test_admin_can_create_update_list_and_deactivate_seat(client: TestClient, seed_data: dict):
    room_id = _seed_room(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    create_response = client.post(
        "/admin/seats",
        json={
            "room_id": room_id,
            "seat_code": "C-01",
            "seat_label": "Corner Seat",
            "is_active": True,
            "is_window_side": True,
            "has_power_socket": True,
            "has_track_socket": False,
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    seat_id = created["id"]

    list_response = client.get("/admin/seats", params={"room_id": room_id})
    assert list_response.status_code == 200
    assert any(item["id"] == seat_id for item in list_response.json()["items"])

    update_response = client.put(
        f"/admin/seats/{seat_id}",
        json={
            "room_id": room_id,
            "seat_code": "C-02",
            "seat_label": "Updated Corner Seat",
            "is_active": True,
            "is_window_side": False,
            "has_power_socket": True,
            "has_track_socket": True,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["seat_code"] == "C-02"
    assert updated["has_track_socket"] is True

    deactivate_response = client.post(f"/admin/seats/{seat_id}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["data"]["is_active"] is False


def test_duplicate_seat_code_in_same_room_is_rejected(client: TestClient, seed_data: dict):
    seeded = _seed_room_with_seat(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.post(
        "/admin/seats",
        json={
            "room_id": seeded["room_id"],
            "seat_code": "B-01",
            "seat_label": "Duplicate Seat",
            "is_active": True,
            "is_window_side": True,
            "has_power_socket": False,
            "has_track_socket": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
