from __future__ import annotations

from datetime import datetime, timedelta, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.errors import BadRequestError
from app.modules.checkin.models.checkin_record import CheckinRecord
from app.modules.checkin.schemas.checkin import StudentCodeCheckinRequest
from app.modules.checkin.services.checkin_service import CheckinService
from app.modules.checkin.services.code_service import CodeService
from app.modules.identity.models.user import User
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


def _login_student(client: TestClient, *, student_no: str, password: str) -> dict[str, str]:
    response = client.post(
        "/student/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_checkin_context(
    seed_data: dict,
    *,
    reservation_status: str = RESERVATION_STATUS_BOOKED,
    reservation_user_id: int | None = None,
    start_offset_minutes: int = -5,
    duration_minutes: int = 60,
    include_second_room: bool = False,
):
    now = datetime.now().replace(second=0, microsecond=0)
    start_time = now + timedelta(minutes=start_offset_minutes)
    end_time = start_time + timedelta(minutes=duration_minutes)
    with SessionLocal() as session:
        room = StudyRoom(
            name="Checkin Room",
            location="Engineering 401",
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
            seat_code="A-01",
            seat_label="Checkin Seat",
            is_active=True,
            is_window_side=True,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.flush()

        second_room_id = None
        if include_second_room:
            second_room = StudyRoom(
                name="Other Room",
                location="Science 401",
                department_id=seed_data["departments"]["cs"],
                is_department_only=True,
                is_active=True,
                open_time=time(8, 0),
                close_time=time(22, 0),
            )
            session.add(second_room)
            session.flush()
            second_room_id = second_room.id

        reservation = Reservation(
            user_id=reservation_user_id or seed_data["users"]["student"],
            seat_id=seat.id,
            room_id=room.id,
            start_time=start_time,
            end_time=end_time,
            status=reservation_status,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.commit()
        return {
            "now": now,
            "room_id": room.id,
            "seat_id": seat.id,
            "reservation_id": reservation.id,
            "reservation_start": start_time,
            "second_room_id": second_room_id,
        }


def _get_reservation_status(reservation_id: int) -> str:
    with SessionLocal() as session:
        reservation = session.get(Reservation, reservation_id)
        assert reservation is not None
        return reservation.status


def test_student_can_check_in_with_dynamic_code(client: TestClient, seed_data: dict):
    context = _seed_checkin_context(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        code = code_service.get_current_dynamic_code(
            context["room_id"],
            now=context["now"],
        )

    response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": context["reservation_id"], "code": code.code},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "CHECKED_IN"
    assert payload["data"]["room_id"] == context["room_id"]
    assert payload["data"]["seat_id"] == context["seat_id"]
    assert payload["data"]["checkin_method"] == "CODE"
    assert _get_reservation_status(context["reservation_id"]) == RESERVATION_STATUS_CHECKED_IN


def test_student_can_check_in_with_qrcode(client: TestClient, seed_data: dict):
    context = _seed_checkin_context(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        token = code_service.generate_qrcode_token(
            room_id=context["room_id"],
            now=context["now"],
        )

    response = client.post(
        "/student/checkins/qrcode",
        headers=headers,
        json={"reservation_id": context["reservation_id"], "token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "CHECKED_IN"
    assert payload["data"]["checkin_method"] == "QRCODE"
    assert _get_reservation_status(context["reservation_id"]) == RESERVATION_STATUS_CHECKED_IN


def test_wrong_dynamic_code_is_rejected(client: TestClient, seed_data: dict):
    context = _seed_checkin_context(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": context["reservation_id"], "code": "999999"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_checkin_code"


def test_non_owner_or_invalid_status_reservations_cannot_check_in(client: TestClient, seed_data: dict):
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )

    non_owner_context = _seed_checkin_context(seed_data, reservation_user_id=seed_data["users"]["target"])
    cancelled_context = _seed_checkin_context(seed_data, reservation_status=RESERVATION_STATUS_CANCELLED)
    checked_in_context = _seed_checkin_context(seed_data, reservation_status=RESERVATION_STATUS_CHECKED_IN)
    expired_context = _seed_checkin_context(seed_data, reservation_status=RESERVATION_STATUS_EXPIRED)

    non_owner_response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": non_owner_context["reservation_id"], "code": "000000"},
    )
    assert non_owner_response.status_code == 403
    assert non_owner_response.json()["code"] == "forbidden"

    cancelled_response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": cancelled_context["reservation_id"], "code": "000000"},
    )
    assert cancelled_response.status_code == 400

    checked_in_response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": checked_in_context["reservation_id"], "code": "000000"},
    )
    assert checked_in_response.status_code == 400

    expired_response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": expired_context["reservation_id"], "code": "000000"},
    )
    assert expired_response.status_code == 400


def test_student_cannot_repeat_successful_checkin(client: TestClient, seed_data: dict):
    context = _seed_checkin_context(seed_data)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        code = code_service.get_current_dynamic_code(
            context["room_id"],
            now=context["now"],
        )

    first_response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": context["reservation_id"], "code": code.code},
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": context["reservation_id"], "code": code.code},
    )
    assert second_response.status_code == 400

    with SessionLocal() as session:
        total_records = session.scalar(
            select(func.count()).select_from(
                select(CheckinRecord.id)
                .where(CheckinRecord.reservation_id == context["reservation_id"])
                .subquery(),
            ),
        )
    assert total_records == 1


def test_checkin_after_grace_window_is_rejected(client: TestClient, seed_data: dict):
    context = _seed_checkin_context(seed_data, start_offset_minutes=-20)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        code = code_service.get_current_dynamic_code(
            context["room_id"],
            now=context["now"],
        )

    response = client.post(
        "/student/checkins/code",
        headers=headers,
        json={"reservation_id": context["reservation_id"], "code": code.code},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_qrcode_must_match_reservation_room(client: TestClient, seed_data: dict):
    context = _seed_checkin_context(seed_data, include_second_room=True)
    headers = _login_student(
        client,
        student_no=seed_data["credentials"]["student_no"],
        password=seed_data["credentials"]["student_password"],
    )
    assert context["second_room_id"] is not None
    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        token = code_service.generate_qrcode_token(
            room_id=context["second_room_id"],
            now=context["now"],
        )

    response = client.post(
        "/student/checkins/qrcode",
        headers=headers,
        json={"reservation_id": context["reservation_id"], "token": token},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_qrcode"


def test_expired_dynamic_code_window_is_rejected(client: TestClient, seed_data: dict):
    context = _seed_checkin_context(seed_data)

    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        old_code = code_service.get_current_dynamic_code(
            context["room_id"],
            now=context["now"] - timedelta(minutes=5),
        )
        student = session.get(User, seed_data["users"]["student"])
        assert student is not None
        with pytest.raises(BadRequestError) as exc_info:
            CheckinService(session, settings=client.app.state.settings).check_in_by_code(
                student,
                StudentCodeCheckinRequest(reservation_id=context["reservation_id"], code=old_code.code),
                now=context["now"],
            )

    assert exc_info.value.code == "invalid_checkin_code"
