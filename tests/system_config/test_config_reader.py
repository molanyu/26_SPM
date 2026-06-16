from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequestError
from app.core.database import SessionLocal
from app.modules.system_config.constants import (
    FIRST_BATCH_CONFIG_KEYS,
    MAX_RESERVATION_HOURS,
    VIOLATION_PENALTY_WINDOW_DAYS,
)
from app.modules.system_config.models.system_config import SystemConfig
from app.modules.system_config.repositories.config_repository import ConfigRepository
from app.modules.system_config.services.config_reader import ConfigReader
from app.modules.system_config.services.config_service import ConfigService


def test_other_modules_can_read_configs_via_public_service(client):
    with SessionLocal() as session:
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


def test_config_reader_initializes_defaults_when_system_config_table_is_empty(client):
    with SessionLocal() as session:
        assert session.query(SystemConfig).count() == 0
        reader = ConfigReader(session)

        assert reader.get_max_reservation_hours() == 4

    with SessionLocal() as session:
        configs = session.query(SystemConfig).all()

    assert {config.config_key for config in configs} == set(FIRST_BATCH_CONFIG_KEYS)


def test_config_reader_initializes_missing_default_without_overwriting_existing_values(client):
    with SessionLocal() as session:
        config_service = ConfigService(session)
        config_service.list_configs()
        config_service.update_config(MAX_RESERVATION_HOURS, 6)
        config = session.query(SystemConfig).filter_by(config_key=VIOLATION_PENALTY_WINDOW_DAYS).one()
        session.delete(config)
        session.commit()

    with SessionLocal() as session:
        reader = ConfigReader(session)

        assert reader.get_violation_penalty_window_days() == 30
        assert reader.get_max_reservation_hours() == 6


def test_config_reader_default_initialization_does_not_commit_pending_caller_changes(client):
    pending_key = "pending_caller_config"
    with SessionLocal() as session:
        session.add(
            SystemConfig(
                config_key=pending_key,
                config_value="1",
                value_type="int",
                description="Should not be committed by config reads.",
            ),
        )
        reader = ConfigReader(session)

        assert reader.get_max_reservation_hours() == 4
        session.rollback()

    with SessionLocal() as session:
        assert session.query(SystemConfig).filter_by(config_key=pending_key).one_or_none() is None
        assert session.query(SystemConfig).filter_by(config_key=MAX_RESERVATION_HOURS).one().config_value == "4"


def test_config_reader_default_initialization_recovers_from_duplicate_insert_race(client, monkeypatch):
    original_create_many = ConfigRepository.create_many
    raced = False

    def racing_create_many(self, configs):
        nonlocal raced
        if not raced:
            raced = True
            with SessionLocal() as competing_session:
                competing_repository = ConfigRepository(competing_session)
                competing_configs = [
                    SystemConfig(
                        config_key=config.config_key,
                        config_value=config.config_value,
                        value_type=config.value_type,
                        description=config.description,
                    )
                    for config in configs
                ]
                original_create_many(competing_repository, competing_configs)
            raise IntegrityError("INSERT system_configs", {}, Exception("duplicate config_key"))
        return original_create_many(self, configs)

    monkeypatch.setattr(ConfigRepository, "create_many", racing_create_many)

    with SessionLocal() as session:
        reader = ConfigReader(session)

        assert reader.get_max_reservation_hours() == 4

    with SessionLocal() as session:
        configs = session.query(SystemConfig).all()

    assert raced
    assert {config.config_key for config in configs} == set(FIRST_BATCH_CONFIG_KEYS)


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
