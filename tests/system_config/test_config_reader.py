from __future__ import annotations

from app.core.database import SessionLocal
from app.modules.system_config.services.config_reader import ConfigReader


def test_other_modules_can_read_configs_via_public_service(client):
    with SessionLocal() as session:
        reader = ConfigReader(session)

        max_reservation_hours = reader.get_max_reservation_hours()
        checkin_grace_minutes = reader.get_checkin_grace_minutes()
        violation_threshold_minutes = reader.get_violation_threshold_minutes()

    assert max_reservation_hours == 4
    assert isinstance(max_reservation_hours, int)
    assert checkin_grace_minutes == 10
    assert isinstance(checkin_grace_minutes, int)
    assert violation_threshold_minutes == 15
    assert isinstance(violation_threshold_minutes, int)
    assert violation_threshold_minutes >= checkin_grace_minutes
