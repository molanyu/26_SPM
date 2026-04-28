from __future__ import annotations

from datetime import datetime, time

from app.core.database import SessionLocal
from app.modules.checkin.models.checkin_code import CheckinCode
from app.modules.checkin.tasks.daily_code_task import generate_daily_checkin_codes
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


def test_daily_code_task_generates_one_code_per_active_room_per_day(client, seed_data: dict):
    room_ids = _seed_rooms(seed_data)
    now = datetime.now().replace(second=0, microsecond=0)
    target_date = now.date()

    with SessionLocal() as session:
        first_run = generate_daily_checkin_codes(
            session,
            run_date=target_date,
            now=now,
            settings=client.app.state.settings,
        )
        second_run = generate_daily_checkin_codes(
            session,
            run_date=target_date,
            now=now,
            settings=client.app.state.settings,
        )

    assert len(first_run) == 2
    assert len(second_run) == 2
    assert sorted(code.room_id for code in first_run) == sorted(room_ids)

    with SessionLocal() as session:
        records = session.query(CheckinCode).order_by(CheckinCode.room_id.asc()).all()
    assert len(records) == 2
    assert sorted(record.room_id for record in records) == sorted(room_ids)
    assert all(record.code_date == target_date for record in records)
