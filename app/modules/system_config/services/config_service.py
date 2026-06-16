from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.modules.system_config.constants import (
    CHECKIN_GRACE_MINUTES,
    FIRST_BATCH_CONFIG_KEYS,
    MAX_RESERVATION_HOURS,
    SYSTEM_CONFIG_DEFINITION_MAP,
    SYSTEM_CONFIG_DEFINITIONS,
    VALUE_TYPE_INT,
    VIOLATION_PENALTY_DURATION_DAYS,
    VIOLATION_PENALTY_THRESHOLD_COUNT,
    VIOLATION_PENALTY_WINDOW_DAYS,
    VIOLATION_THRESHOLD_MINUTES,
)
from app.modules.system_config.models.system_config import SystemConfig
from app.modules.system_config.repositories.config_repository import ConfigRepository


class ConfigService:
    def __init__(self, session: Session) -> None:
        self.repository = ConfigRepository(session)

    def list_configs(self) -> list[SystemConfig]:
        configs = self._ensure_required_configs()
        return [configs[config_key] for config_key in FIRST_BATCH_CONFIG_KEYS]

    def update_config(self, config_key: str, raw_value: object) -> SystemConfig:
        definition = SYSTEM_CONFIG_DEFINITION_MAP.get(config_key)
        if definition is None:
            raise NotFoundError("System config does not exist.")

        configs = self._ensure_required_configs()
        config = configs[config_key]
        normalized_value = self._validate_and_normalize_value(config_key, raw_value)

        effective_values = {
            key: self.parse_config_value(item)
            for key, item in configs.items()
        }
        effective_values[config_key] = self._coerce_definition_value(config_key, raw_value)
        self._validate_cross_config_rules(effective_values)

        config.config_value = normalized_value
        return self.repository.save(config)

    def get_config(self, config_key: str) -> SystemConfig:
        definition = SYSTEM_CONFIG_DEFINITION_MAP.get(config_key)
        if definition is None:
            raise NotFoundError("System config does not exist.")
        config = self.repository.get_by_key(definition.config_key)
        if config is None:
            raise BadRequestError("Required system config is missing.")
        return config

    def parse_config_value(self, config: SystemConfig) -> int:
        if config.value_type != VALUE_TYPE_INT:
            raise BadRequestError("Unsupported system config value_type.")
        try:
            value = int(config.config_value)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("Stored system config value is invalid.") from exc
        self._validate_int_range(config.config_key, value)
        return value

    def _ensure_required_configs(self) -> dict[str, SystemConfig]:
        existing = {
            config.config_key: config
            for config in self.repository.list_by_keys(FIRST_BATCH_CONFIG_KEYS)
        }
        missing = []
        for definition in SYSTEM_CONFIG_DEFINITIONS:
            if definition.config_key in existing:
                continue
            config = SystemConfig(
                config_key=definition.config_key,
                config_value=definition.default_value,
                value_type=definition.value_type,
                description=definition.description,
            )
            existing[definition.config_key] = config
            missing.append(config)
        if missing:
            self.repository.create_many(missing)
        return existing

    def _validate_and_normalize_value(self, config_key: str, raw_value: object) -> str:
        definition = SYSTEM_CONFIG_DEFINITION_MAP[config_key]
        if definition.value_type != VALUE_TYPE_INT:
            raise BadRequestError("Unsupported system config value_type.")
        return str(self._coerce_definition_value(config_key, raw_value))

    def _coerce_definition_value(self, config_key: str, raw_value: object) -> int:
        if isinstance(raw_value, bool):
            raise BadRequestError("config_value must match the declared value_type.")
        if isinstance(raw_value, int):
            value = raw_value
        elif isinstance(raw_value, str):
            cleaned = raw_value.strip()
            if not cleaned:
                raise BadRequestError("config_value must not be blank.")
            try:
                value = int(cleaned)
            except ValueError as exc:
                raise BadRequestError("config_value must match the declared value_type.") from exc
        else:
            raise BadRequestError("config_value must match the declared value_type.")

        self._validate_int_range(config_key, value)
        return value

    def _validate_int_range(self, config_key: str, value: int) -> None:
        if config_key == MAX_RESERVATION_HOURS and value <= 0:
            raise BadRequestError("max_reservation_hours must be a positive integer.")
        if config_key in {CHECKIN_GRACE_MINUTES, VIOLATION_THRESHOLD_MINUTES} and value < 0:
            raise BadRequestError(f"{config_key} must be a non-negative integer.")
        if config_key in {
            VIOLATION_PENALTY_THRESHOLD_COUNT,
            VIOLATION_PENALTY_WINDOW_DAYS,
            VIOLATION_PENALTY_DURATION_DAYS,
        } and value <= 0:
            raise BadRequestError(f"{config_key} must be a positive integer.")

    def _validate_cross_config_rules(self, values: dict[str, int]) -> None:
        if values[VIOLATION_THRESHOLD_MINUTES] < values[CHECKIN_GRACE_MINUTES]:
            raise BadRequestError(
                "violation_threshold_minutes must be greater than or equal to checkin_grace_minutes.",
            )
