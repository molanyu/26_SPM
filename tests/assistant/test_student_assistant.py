from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from datetime import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.modules.assistant.services.intent_service import IntentService
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CHECKED_IN,
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


def _seed_assistant_resources(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        cs_room = StudyRoom(
            name="Assistant CS Room",
            location="Engineering 501",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        public_room = StudyRoom(
            name="Assistant Public Room",
            location="Library 101",
            department_id=None,
            is_department_only=False,
            is_active=True,
            open_time=time(9, 0),
            close_time=time(21, 0),
        )
        math_room = StudyRoom(
            name="Assistant Math Room",
            location="Science 601",
            department_id=seed_data["departments"]["math"],
            is_department_only=True,
            is_active=True,
            open_time=time(9, 0),
            close_time=time(21, 0),
        )
        session.add_all([cs_room, public_room, math_room])
        session.flush()

        seats = [
            Seat(
                room_id=cs_room.id,
                seat_code="A-01",
                seat_label="CS Window Seat",
                is_active=True,
                is_window_side=True,
                has_power_socket=False,
                has_track_socket=False,
            ),
            Seat(
                room_id=cs_room.id,
                seat_code="A-02",
                seat_label="CS Power Seat",
                is_active=True,
                is_window_side=False,
                has_power_socket=True,
                has_track_socket=False,
            ),
            Seat(
                room_id=cs_room.id,
                seat_code="A-03",
                seat_label="CS Track Seat",
                is_active=True,
                is_window_side=False,
                has_power_socket=False,
                has_track_socket=True,
            ),
            Seat(
                room_id=public_room.id,
                seat_code="P-01",
                seat_label="Public Window Seat",
                is_active=True,
                is_window_side=True,
                has_power_socket=True,
                has_track_socket=False,
            ),
            Seat(
                room_id=math_room.id,
                seat_code="M-01",
                seat_label="Math Window Seat",
                is_active=True,
                is_window_side=True,
                has_power_socket=True,
                has_track_socket=True,
            ),
        ]
        session.add_all(seats)
        session.commit()

        return {
            "cs_room": cs_room.id,
            "public_room": public_room.id,
            "math_room": math_room.id,
            "cs_window_seat": seats[0].id,
            "cs_power_seat": seats[1].id,
            "cs_track_seat": seats[2].id,
            "public_window_seat": seats[3].id,
            "math_window_seat": seats[4].id,
        }


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


def _today_slot(start_hour: int, duration_hours: int = 2) -> tuple[datetime, datetime]:
    start_time = datetime.combine(dt_date.today(), time(start_hour, 0))
    end_time = start_time + timedelta(hours=duration_hours)
    return start_time, end_time


def test_intent_service_recognizes_supported_queries() -> None:
    service = IntentService()

    available_query = service.parse_message("今天晚上还有空座吗")
    assert available_query.intent == "QUERY_AVAILABLE_SEATS"
    assert available_query.seat_attribute is None

    reservation_query = service.parse_message("我今天定了哪里的座位")
    assert reservation_query.intent == "QUERY_TODAY_MY_RESERVATION"
    assert reservation_query.seat_attribute is None


@pytest.mark.parametrize(
    ("message", "expected_attribute"),
    [
        ("帮我找靠窗的座位", "WINDOW"),
        ("帮我找固定插座的座位", "POWER_SOCKET"),
        ("帮我找移动导轨插座的座位", "TRACK_SOCKET"),
    ],
)
def test_intent_service_extracts_supported_seat_attributes(
    message: str,
    expected_attribute: str,
) -> None:
    parsed = IntentService().parse_message(message)

    assert parsed.intent == "QUERY_WINDOW_SEATS"
    assert parsed.seat_attribute == expected_attribute


def test_student_assistant_query_returns_available_seats_for_tonight(client: TestClient, seed_data: dict) -> None:
    resource_ids = _seed_assistant_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _today_slot(19, duration_hours=2)
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["cs_window_seat"],
        room_id=resource_ids["cs_room"],
        start_time=start_time,
        end_time=end_time,
    )

    response = client.post(
        "/student/assistant/query",
        headers=headers,
        json={"message": "今天晚上还有空座吗"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "QUERY_AVAILABLE_SEATS"
    assert payload["result_type"] == "AVAILABLE_SEAT_LIST"
    returned_codes = {item["seat_code"] for item in payload["result"]["items"]}
    assert "A-01" not in returned_codes
    assert {"A-02", "A-03", "P-01"}.issubset(returned_codes)
    assert all(item["available_time_range"] for item in payload["result"]["items"])


def test_student_assistant_query_returns_matching_window_seats(client: TestClient, seed_data: dict) -> None:
    _seed_assistant_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    response = client.post(
        "/student/assistant/query",
        headers=headers,
        json={"message": "帮我找靠窗的座位"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "QUERY_WINDOW_SEATS"
    assert payload["result"]["requested_attribute"] == "WINDOW"
    returned_codes = {item["seat_code"] for item in payload["result"]["items"]}
    assert returned_codes == {"A-01", "P-01"}


def test_student_assistant_query_excludes_checked_in_seats_from_tonight_availability(
    client: TestClient,
    seed_data: dict,
) -> None:
    resource_ids = _seed_assistant_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    start_time, end_time = _today_slot(18, duration_hours=3)
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["cs_power_seat"],
        room_id=resource_ids["cs_room"],
        start_time=start_time,
        end_time=end_time,
        status=RESERVATION_STATUS_CHECKED_IN,
    )

    response = client.post(
        "/student/assistant/query",
        headers=headers,
        json={"message": "今天晚上还有空座吗"},
    )

    assert response.status_code == 200
    payload = response.json()
    returned_codes = {item["seat_code"] for item in payload["result"]["items"]}
    assert "A-02" not in returned_codes


def test_student_assistant_query_returns_matching_track_socket_seats(client: TestClient, seed_data: dict) -> None:
    _seed_assistant_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    response = client.post(
        "/student/assistant/query",
        headers=headers,
        json={"message": "帮我找移动导轨插座的座位"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "QUERY_WINDOW_SEATS"
    assert payload["result"]["requested_attribute"] == "TRACK_SOCKET"
    returned_codes = {item["seat_code"] for item in payload["result"]["items"]}
    assert returned_codes == {"A-03"}


def test_student_assistant_query_returns_today_reservations_for_current_student_only(
    client: TestClient,
    seed_data: dict,
) -> None:
    resource_ids = _seed_assistant_resources(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    today_start, today_end = _today_slot(14, duration_hours=1)
    tomorrow_start = today_start + timedelta(days=1)
    tomorrow_end = today_end + timedelta(days=1)
    own_reservation_id = _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["cs_power_seat"],
        room_id=resource_ids["cs_room"],
        start_time=today_start,
        end_time=today_end,
    )
    _insert_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=resource_ids["public_window_seat"],
        room_id=resource_ids["public_room"],
        start_time=tomorrow_start,
        end_time=tomorrow_end,
    )
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        seat_id=resource_ids["cs_track_seat"],
        room_id=resource_ids["cs_room"],
        start_time=today_start,
        end_time=today_end,
    )

    response = client.post(
        "/student/assistant/query",
        headers=headers,
        json={"message": "我今天定了哪里的座位"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "QUERY_TODAY_MY_RESERVATION"
    items = payload["result"]["items"]
    assert len(items) == 1
    assert items[0]["reservation_id"] == own_reservation_id
    assert items[0]["room_id"] == resource_ids["cs_room"]


def test_student_assistant_query_returns_controlled_failure_for_unknown_message(
    client: TestClient,
    seed_data: dict,
) -> None:
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    response = client.post(
        "/student/assistant/query",
        headers=headers,
        json={"message": "图书馆什么时候建成的"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] is None
    assert payload["result_type"] == "CONTROLLED_FAILURE"
    assert payload["result"]["code"] == "INTENT_NOT_RECOGNIZED"
