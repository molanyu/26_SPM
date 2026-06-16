from __future__ import annotations

import pytest

from app.core.errors import BadRequestError
from app.core.database import SessionLocal
from app.modules.system_config.constants import VIOLATION_PENALTY_WINDOW_DAYS
from app.modules.system_config.models.system_config import SystemConfig
from app.modules.system_config.services.config_reader import ConfigReader
from app.modules.system_config.services.config_service import ConfigService


def test_other_modules_can_read_configs_via_public_service(client):
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        reader = ConfigReader(session)

        max_reservation_hours = reader.get_max_reservation_hours()
        checkin_grace_minutes = reader.get_checkin_grace_minutes()
        violation_threshold_minutes = reader.get_violation_threshold_minutes()
        penalty_threshold_count = reader.get_violation_penalty_threshold_count()
        penalty_window_days = reader.get_violation_penalty_window_days()
        penalty_duration_days = reader.get_violation_penalty_duration_days()

    assert max_reservation_hours == 4
    assert isinstance(max_reservation_hours, int)
    assert checkin_grace_minutes == 10
    assert isinstance(checkin_grace_minutes, int)
    assert violation_threshold_minutes == 15
    assert isinstance(violation_threshold_minutes, int)
    assert violation_threshold_minutes >= checkin_grace_minutes
    assert penalty_threshold_count == 3
    assert isinstance(penalty_threshold_count, int)
    assert penalty_window_days == 30
    assert isinstance(penalty_window_days, int)
    assert penalty_duration_days == 7
    assert isinstance(penalty_duration_days, int)


def test_config_reader_raises_controlled_error_when_required_config_is_missing(client):
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        config = session.query(SystemConfig).filter_by(config_key=VIOLATION_PENALTY_WINDOW_DAYS).one()
        session.delete(config)
        session.commit()

    with SessionLocal() as session:
        reader = ConfigReader(session)
        with pytest.raises(BadRequestError):
            reader.get_violation_penalty_window_days()


def test_config_reader_raises_controlled_error_when_stored_value_has_wrong_type(client):
    with SessionLocal() as session:
        ConfigService(session).list_configs()
        config = session.query(SystemConfig).filter_by(config_key=VIOLATION_PENALTY_WINDOW_DAYS).one()
        config.config_value = "not-an-int"
        session.commit()

    with SessionLocal() as session:
        reader = ConfigReader(session)
        with pytest.raises(BadRequestError):
            reader.get_violation_penalty_window_days()
