from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, time
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.errors import AppError
from app.core.database import SessionLocal
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.reservation.schemas.reservation import StudentReservationCreateRequest
from app.modules.reservation.services.reservation_service import ReservationService
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.system_config.services.config_service import ConfigService
from app.modules.violation.models.violation_record import VIOLATION_TYPE_NO_SHOW_TIMEOUT, ViolationRecord
from app.modules.violation.services.violation_service import ViolationService

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
MINIPROGRAM_RESERVATIONS_JS = WORKSPACE_ROOT / "miniprogram" / "pages" / "reservations" / "reservations.js"
MINIPROGRAM_RESERVATIONS_WXML = WORKSPACE_ROOT / "miniprogram" / "pages" / "reservations" / "reservations.wxml"


def _login_student(client: TestClient, *, student_no: str, password: str) -> dict[str, str]:
    response = client.post(
        "/student/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_reservation_resources(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        cs_room = StudyRoom(
            name="CS Booking Room",
            location="Engineering 201",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        math_room = StudyRoom(
            name="Math Booking Room",
            location="Science 201",
            department_id=seed_data["departments"]["math"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        inactive_room = StudyRoom(
            name="Inactive Booking Room",
            location="Old Building",
            department_id=None,
            is_department_only=False,
            is_active=False,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add_all([cs_room, math_room, inactive_room])
        session.flush()

        cs_seat = Seat(
            room_id=cs_room.id,
            seat_code="A-01",
            seat_label="CS Seat",
            is_active=True,
            is_window_side=True,
            has_power_socket=True,
            has_track_socket=False,
        )
        cs_second_seat = Seat(
            room_id=cs_room.id,
            seat_code="A-03",
            seat_label="CS Second Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        cs_third_seat = Seat(
            room_id=cs_room.id,
            seat_code="A-04",
            seat_label="CS Third Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=False,
            has_track_socket=True,
        )
        cs_fourth_seat = Seat(
            room_id=cs_room.id,
            seat_code="A-05",
            seat_label="CS Fourth Seat",
            is_active=True,
            is_window_side=True,
            has_power_socket=False,
            has_track_socket=False,
        )
        math_seat = Seat(
            room_id=math_room.id,
            seat_code="B-01",
            seat_label="Math Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=True,
        )
        inactive_seat = Seat(
            room_id=cs_room.id,
            seat_code="A-02",
            seat_label="Inactive Seat",
            is_active=False,
            is_window_side=False,
            has_power_socket=False,
            has_track_socket=False,
        )
        inactive_room_seat = Seat(
            room_id=inactive_room.id,
            seat_code="C-01",
            seat_label="Inactive Room Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=False,
            has_track_socket=False,
        )
        session.add_all(
            [
                cs_seat,
                cs_second_seat,
                cs_third_seat,
                cs_fourth_seat,
                math_seat,
                inactive_seat,
                inactive_room_seat,
            ],
        )
        session.commit()

        return {
            "cs_room": cs_room.id,
            "math_room": math_room.id,
            "inactive_room": inactive_room.id,
            "cs_seat": cs_seat.id,
            "cs_second_seat": cs_second_seat.id,
            "cs_third_seat": cs_third_seat.id,
            "cs_fourth_seat": cs_fourth_seat.id,
            "math_seat": math_seat.id,
            "inactive_seat": inactive_seat.id,
            "inactive_room_seat": inactive_room_seat.id,
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
    status: str = RESERVATION_STATUS_BOOKED,
) -> int:
    with SessionLocal() as session:
        reservation = Reservation(
            user_id=user_id,
            seat_id=seat_id,
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            status=status,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.commit()
        return reservation.id


def _seed_active_penalty_records(seed_data: dict, resource_ids: dict[str, int]) -> None:
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    occurred_times = [
        now - timedelta(days=3),
        now - timedelta(days=2),
        now - timedelta(days=1),
    ]
    with SessionLocal() as session:
        for index, occurred_at in enumerate(occurred_times):
            reservation = Reservation(
                user_id=seed_data["users"]["student"],
                seat_id=resource_ids["cs_seat"],
                room_id=resource_ids["cs_room"],
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
                    user_id=seed_data["users"]["student"],
                    reservation_id=reservation.id,
                    violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                    occurred_at=occurred_at,
                    remark=f"Penalty seed {index}",
                ),
            )
        session.commit()


def test_student_can_create_reservation(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "BOOKED"
    assert payload["data"]["seat_id"] == resource_ids["cs_seat"]
    assert payload["data"]["room_id"] == resource_ids["cs_room"]


def test_student_can_create_half_hour_reservation(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=9, start_minute=30, duration_hours=1)

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["start_time"] == start_time.isoformat()
    assert payload["end_time"] == end_time.isoformat()


def test_non_half_hour_reservation_is_rejected(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)
    start_time = start_time.replace(minute=15)

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_past_reservation_is_rejected(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    end_time = start_time + timedelta(hours=1)

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_reservation_exceeding_max_hours_is_rejected(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=5)

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_reservation_outside_open_hours_is_rejected(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=7, duration_hours=2)

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_invisible_or_inactive_resources_are_rejected(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    invisible_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["math_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert invisible_response.status_code == 403
    assert invisible_response.json()["code"] == "forbidden"

    inactive_seat_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["inactive_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert inactive_seat_response.status_code == 400
    assert inactive_seat_response.json()["code"] == "bad_request"

    inactive_room_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["inactive_room_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert inactive_room_response.status_code == 400
    assert inactive_room_response.json()["code"] == "bad_request"


def test_penalized_student_cannot_create_reservation_before_write(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    _seed_active_penalty_records(seed_data, resource_ids)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    with SessionLocal() as session:
        before_count = session.query(Reservation).count()

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_second_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"
    with SessionLocal() as session:
        assert session.query(Reservation).count() == before_count


def test_manually_blocked_student_cannot_create_reservation_before_write(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    with SessionLocal() as session:
        ViolationService(session).activate_manual_reservation_block(
            seed_data["users"]["student"],
            "Manual block before student reservation",
            seed_data["users"]["admin"],
        )
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    with SessionLocal() as session:
        before_count = session.query(Reservation).count()

    response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_second_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"
    with SessionLocal() as session:
        assert session.query(Reservation).count() == before_count


def test_conflicting_reservation_is_rejected(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    first_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": (start_time + timedelta(hours=1)).isoformat(),
            "end_time": (end_time + timedelta(hours=1)).isoformat(),
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["code"] == "conflict"


def test_student_room_seat_availability_marks_only_booked_and_checked_in_overlaps_as_occupied(
    client: TestClient,
    seed_data: dict,
):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=12, duration_hours=2)
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["cs_seat"],
        room_id=resource_ids["cs_room"],
        start_time=start_time + timedelta(minutes=30),
        end_time=end_time + timedelta(minutes=30),
        status=RESERVATION_STATUS_BOOKED,
    )
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["cs_second_seat"],
        room_id=resource_ids["cs_room"],
        start_time=start_time,
        end_time=end_time,
        status=RESERVATION_STATUS_CHECKED_IN,
    )
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["cs_third_seat"],
        room_id=resource_ids["cs_room"],
        start_time=start_time,
        end_time=end_time,
        status=RESERVATION_STATUS_CANCELLED,
    )
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["cs_fourth_seat"],
        room_id=resource_ids["cs_room"],
        start_time=start_time,
        end_time=end_time,
        status=RESERVATION_STATUS_EXPIRED,
    )

    response = client.get(
        f"/student/rooms/{resource_ids['cs_room']}/seat-availability",
        headers=headers,
        params={
            "date": start_time.date().isoformat(),
            "start_time": start_time.time().isoformat(),
            "end_time": end_time.time().isoformat(),
        },
    )

    assert response.status_code == 200
    statuses = {item["seat_id"]: item["status"] for item in response.json()["items"]}
    assert statuses[resource_ids["cs_seat"]] == "OCCUPIED"
    assert statuses[resource_ids["cs_second_seat"]] == "OCCUPIED"
    assert statuses[resource_ids["cs_third_seat"]] == "AVAILABLE"
    assert statuses[resource_ids["cs_fourth_seat"]] == "AVAILABLE"


def test_student_room_seat_availability_respects_resource_visibility_and_attribute_filters(
    client: TestClient,
    seed_data: dict,
):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=12, duration_hours=2)

    filtered_response = client.get(
        f"/student/rooms/{resource_ids['cs_room']}/seat-availability",
        headers=headers,
        params={
            "date": start_time.date().isoformat(),
            "start_time": start_time.time().isoformat(),
            "end_time": end_time.time().isoformat(),
            "has_track_socket": "true",
        },
    )

    assert filtered_response.status_code == 200
    assert {item["seat_id"] for item in filtered_response.json()["items"]} == {resource_ids["cs_third_seat"]}

    invisible_response = client.get(
        f"/student/rooms/{resource_ids['math_room']}/seat-availability",
        headers=headers,
        params={
            "date": start_time.date().isoformat(),
            "start_time": start_time.time().isoformat(),
            "end_time": end_time.time().isoformat(),
        },
    )

    assert invisible_response.status_code == 404
    assert invisible_response.json()["code"] == "not_found"


def test_student_room_seat_availability_rejects_time_outside_open_hours(
    client: TestClient,
    seed_data: dict,
):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=7, duration_hours=1)

    response = client.get(
        f"/student/rooms/{resource_ids['cs_room']}/seat-availability",
        headers=headers,
        params={
            "date": start_time.date().isoformat(),
            "start_time": start_time.time().isoformat(),
            "end_time": end_time.time().isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_same_student_overlapping_reservation_on_different_seat_is_rejected(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    first_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_second_seat"],
            "start_time": (start_time + timedelta(minutes=30)).isoformat(),
            "end_time": (end_time + timedelta(minutes=30)).isoformat(),
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["code"] == "conflict"


def test_concurrent_student_reservation_writes_reject_overlap(seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)
    student = SimpleNamespace(
        id=seed_data["users"]["student"],
        department_id=seed_data["departments"]["cs"],
    )
    barrier = Barrier(2)

    def attempt_create() -> tuple[str, int | str]:
        session = SessionLocal()
        service = ReservationService(session)
        payload = StudentReservationCreateRequest(
            seat_id=resource_ids["cs_seat"],
            start_time=start_time,
            end_time=end_time,
        )
        barrier.wait()
        try:
            reservation = service.create_student_reservation(student, payload)
            return ("created", reservation.id)
        except AppError as exc:
            return ("error", exc.code)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt_create(), range(2)))

    assert sum(1 for kind, _ in results if kind == "created") == 1
    assert sum(1 for kind, value in results if kind == "error" and value == "conflict") == 1


def test_concurrent_same_user_reservations_on_different_seats_reject_overlap(seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)
    student = SimpleNamespace(
        id=seed_data["users"]["student"],
        department_id=seed_data["departments"]["cs"],
    )
    barrier = Barrier(2)

    def attempt_create(seat_id: int) -> tuple[str, int | str]:
        session = SessionLocal()
        service = ReservationService(session)
        payload = StudentReservationCreateRequest(
            seat_id=seat_id,
            start_time=start_time,
            end_time=end_time,
        )
        barrier.wait()
        try:
            reservation = service.create_student_reservation(student, payload)
            return ("created", reservation.id)
        except AppError as exc:
            return ("error", exc.code)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt_create, [resource_ids["cs_seat"], resource_ids["cs_second_seat"]]))

    assert sum(1 for kind, _ in results if kind == "created") == 1
    assert sum(1 for kind, value in results if kind == "error" and value == "conflict") == 1

    with SessionLocal() as session:
        active_overlap_count = int(
            session.scalar(
                select(func.count())
                .select_from(Reservation)
                .where(
                    Reservation.user_id == seed_data["users"]["student"],
                    Reservation.status.in_((RESERVATION_STATUS_BOOKED, RESERVATION_STATUS_CHECKED_IN)),
                    Reservation.start_time < end_time,
                    Reservation.end_time > start_time,
                )
            )
            or 0,
        )

    assert active_overlap_count == 1


def test_student_can_query_history_and_cancel_before_start(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    create_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert create_response.status_code == 200
    reservation_id = create_response.json()["data"]["reservation_id"]

    cancel_response = client.post(
        f"/student/reservations/{reservation_id}/cancel",
        headers=headers,
        json={"reason": "Change of plans"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "CANCELLED"

    history_response = client.get("/student/reservations/history", headers=headers)
    assert history_response.status_code == 200
    history_items = history_response.json()["items"]
    assert any(item["reservation_id"] == reservation_id and item["status"] == "CANCELLED" for item in history_items)


def test_student_can_query_current_reservations(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    ongoing_id = _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["cs_seat"],
        room_id=resource_ids["cs_room"],
        start_time=current_hour - timedelta(hours=1),
        end_time=current_hour + timedelta(hours=1),
        status=RESERVATION_STATUS_CHECKED_IN,
    )
    future_id = _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["cs_seat"],
        room_id=resource_ids["cs_room"],
        start_time=current_hour + timedelta(hours=2),
        end_time=current_hour + timedelta(hours=3),
        status=RESERVATION_STATUS_BOOKED,
    )
    _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["cs_seat"],
        room_id=resource_ids["cs_room"],
        start_time=current_hour - timedelta(hours=5),
        end_time=current_hour - timedelta(hours=4),
        status=RESERVATION_STATUS_BOOKED,
    )
    _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["cs_seat"],
        room_id=resource_ids["cs_room"],
        start_time=current_hour + timedelta(hours=4),
        end_time=current_hour + timedelta(hours=5),
        status=RESERVATION_STATUS_CANCELLED,
    )

    response = client.get("/student/reservations/current", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [item["reservation_id"] for item in payload["items"]] == [ongoing_id, future_id]
    assert all(item["status"] in {"BOOKED", "CHECKED_IN"} for item in payload["items"])


def test_student_cannot_cancel_started_or_other_users_reservation(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    past_start = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    past_end = past_start + timedelta(hours=1)
    own_started_reservation_id = _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["cs_seat"],
        room_id=resource_ids["cs_room"],
        start_time=past_start,
        end_time=past_end,
    )

    started_cancel_response = client.post(
        f"/student/reservations/{own_started_reservation_id}/cancel",
        headers=headers,
        json={"reason": "Too late"},
    )
    assert started_cancel_response.status_code == 400
    assert started_cancel_response.json()["code"] == "bad_request"

    future_start, future_end = _future_slot(start_hour=14, duration_hours=1)
    other_reservation_id = _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["math_seat"],
        room_id=resource_ids["math_room"],
        start_time=future_start,
        end_time=future_end,
    )

    other_cancel_response = client.post(
        f"/student/reservations/{other_reservation_id}/cancel",
        headers=headers,
        json={"reason": "Not mine"},
    )
    assert other_cancel_response.status_code == 403
    assert other_cancel_response.json()["code"] == "forbidden"


def test_student_can_rebook_from_history_record(client: TestClient, seed_data: dict):
    resource_ids = _seed_reservation_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _future_slot(days=2, start_hour=10, duration_hours=2)

    create_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": resource_ids["cs_seat"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert create_response.status_code == 200
    reservation_id = create_response.json()["data"]["reservation_id"]

    cancel_response = client.post(
        f"/student/reservations/{reservation_id}/cancel",
        headers=headers,
        json={"reason": "Need to rebook later"},
    )
    assert cancel_response.status_code == 200

    history_response = client.get("/student/reservations/history", headers=headers)
    assert history_response.status_code == 200
    history_item = next(item for item in history_response.json()["items"] if item["reservation_id"] == reservation_id)
    assert history_item["seat_id"] == resource_ids["cs_seat"]
    assert history_item["start_time"] == start_time.isoformat()
    assert history_item["end_time"] == end_time.isoformat()

    rebook_response = client.post(
        "/student/reservations",
        headers=headers,
        json={
            "seat_id": history_item["seat_id"],
            "start_time": history_item["start_time"],
            "end_time": history_item["end_time"],
        },
    )

    assert rebook_response.status_code == 200
    assert rebook_response.json()["data"]["reservation_id"] != reservation_id
    assert rebook_response.json()["data"]["seat_id"] == resource_ids["cs_seat"]


def test_miniprogram_history_page_keeps_rebook_entry_visible_for_all_history_items() -> None:
    reservations_js = MINIPROGRAM_RESERVATIONS_JS.read_text(encoding="utf-8")
    reservations_wxml = MINIPROGRAM_RESERVATIONS_WXML.read_text(encoding="utf-8")

    assert 'bindtap="rebookReservation"' in reservations_wxml
    assert 'data-seat-id="{{item.seat_id}}"' in reservations_wxml
    assert "canRebook: true" in reservations_js
    assert "historyItems = this.decorateReservations" in reservations_js
    assert "!currentIds.has(String(item.reservation_id))" in reservations_js


def test_miniprogram_reservation_page_hides_cancel_for_started_booked_reservation() -> None:
    reservations_js = MINIPROGRAM_RESERVATIONS_JS.read_text(encoding="utf-8")
    reservations_wxml = MINIPROGRAM_RESERVATIONS_WXML.read_text(encoding="utf-8")

    assert "startMs > nowMs" in reservations_js
    assert "item.status === 'BOOKED' && startMs <= nowMs && endMs >= nowMs" in reservations_js
    assert "待签到（不可取消）" in reservations_js
    assert "超时未签到（已记违约）" in reservations_js
    assert "状态：{{item.statusLabel}}" in reservations_wxml
