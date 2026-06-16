from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.system_config.constants import (
    CHECKIN_GRACE_MINUTES,
    MAX_RESERVATION_HOURS,
    VIOLATION_PENALTY_DURATION_DAYS,
    VIOLATION_PENALTY_THRESHOLD_COUNT,
    VIOLATION_PENALTY_WINDOW_DAYS,
    VIOLATION_THRESHOLD_MINUTES,
)
from app.modules.system_config.services.config_service import ConfigService


class ConfigReader:
    def __init__(self, session: Session) -> None:
        self.config_service = ConfigService(session)

    def get_max_reservation_hours(self) -> int:
        return self._get_int(MAX_RESERVATION_HOURS)

    def get_checkin_grace_minutes(self) -> int:
        return self._get_int(CHECKIN_GRACE_MINUTES)

    def get_violation_threshold_minutes(self) -> int:
        return self._get_int(VIOLATION_THRESHOLD_MINUTES)

    def get_violation_penalty_threshold_count(self) -> int:
        return self._get_int(VIOLATION_PENALTY_THRESHOLD_COUNT)

    def get_violation_penalty_window_days(self) -> int:
        return self._get_int(VIOLATION_PENALTY_WINDOW_DAYS)

    def get_violation_penalty_duration_days(self) -> int:
        return self._get_int(VIOLATION_PENALTY_DURATION_DAYS)

    def _get_int(self, config_key: str) -> int:
        config = self.config_service.get_config(config_key)
        return self.config_service.parse_config_value(config)
