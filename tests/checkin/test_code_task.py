from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from app.core.database import SessionLocal
from app.core.errors import BadRequestError
from app.modules.checkin.models.checkin_code import CheckinCode
from app.modules.checkin.services.code_service import CodeService
from app.modules.checkin.tasks.daily_code_task import get_current_dynamic_checkin_codes
from app.modules.resource.models.study_room import StudyRoom


def _seed_rooms(seed_data: dict) -> tuple[int, int]:
    with SessionLocal() as session:
        first_room = StudyRoom(
            name="Task Room A",
            location="Engineering 501",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        second_room = StudyRoom(
            name="Task Room B",
            location="Engineering 502",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add_all([first_room, second_room])
        session.commit()
        return first_room.id, second_room.id


def test_dynamic_code_is_stable_within_same_five_minute_window(client, seed_data: dict):
    first_room_id, _ = _seed_rooms(seed_data)
    now = datetime(2026, 1, 2, 9, 31, 15)
    same_window = datetime(2026, 1, 2, 9, 34, 59)

    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        first_code = code_service.get_current_dynamic_code(first_room_id, now=now)
        second_code = code_service.get_current_dynamic_code(first_room_id, now=same_window)

    assert first_code.code == second_code.code
    assert first_code.time_slice_start == datetime(2026, 1, 2, 9, 30)
    assert first_code.expires_at == datetime(2026, 1, 2, 9, 35)


def test_dynamic_code_changes_across_five_minute_windows(client, seed_data: dict):
    first_room_id, _ = _seed_rooms(seed_data)
    now = datetime(2026, 1, 2, 9, 34, 59)
    next_window = now + timedelta(seconds=1)

    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        current_code = code_service.get_current_dynamic_code(first_room_id, now=now)
        next_code = code_service.get_current_dynamic_code(first_room_id, now=next_window)

    assert current_code.time_slice_start == datetime(2026, 1, 2, 9, 30)
    assert next_code.time_slice_start == datetime(2026, 1, 2, 9, 35)
    assert current_code.code != next_code.code


def test_dynamic_code_differs_between_rooms_in_same_window(client, seed_data: dict):
    first_room_id, second_room_id = _seed_rooms(seed_data)
    now = datetime(2026, 1, 2, 9, 31, 15)

    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        first_code = code_service.get_current_dynamic_code(first_room_id, now=now)
        second_code = code_service.get_current_dynamic_code(second_room_id, now=now)

    assert first_code.time_slice_start == second_code.time_slice_start
    assert first_code.code != second_code.code


def test_dynamic_code_task_returns_current_codes_without_creating_daily_rows(client, seed_data: dict):
    room_ids = _seed_rooms(seed_data)
    now = datetime(2026, 1, 2, 9, 31, 15)

    with SessionLocal() as session:
        first_run = get_current_dynamic_checkin_codes(
            session,
            now=now,
            settings=client.app.state.settings,
        )
        second_run = get_current_dynamic_checkin_codes(
            session,
            now=now,
            settings=client.app.state.settings,
        )

    assert len(first_run) == 2
    assert len(second_run) == 2
    assert sorted(code.room_id for code in first_run) == sorted(room_ids)
    assert [code.code for code in first_run] == [code.code for code in second_run]

    with SessionLocal() as session:
        records = session.query(CheckinCode).order_by(CheckinCode.room_id.asc()).all()
    assert records == []


def test_qrcode_token_expires_after_current_five_minute_window(client, seed_data: dict):
    first_room_id, _ = _seed_rooms(seed_data)
    now = datetime(2026, 1, 2, 9, 31, 15)

    with SessionLocal() as session:
        code_service = CodeService(session, settings=client.app.state.settings)
        token = code_service.generate_qrcode_token(room_id=first_room_id, now=now)
        with pytest.raises(BadRequestError) as exc_info:
            code_service.validate_qrcode_token(
                room_id=first_room_id,
                token=token,
                now=datetime(2026, 1, 2, 9, 35, 0),
            )

    assert exc_info.value.code == "invalid_qrcode"
