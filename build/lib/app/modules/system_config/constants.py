from __future__ import annotations

from dataclasses import dataclass

VALUE_TYPE_INT = "int"

MAX_RESERVATION_HOURS = "max_reservation_hours"
CHECKIN_GRACE_MINUTES = "checkin_grace_minutes"
VIOLATION_THRESHOLD_MINUTES = "violation_threshold_minutes"


@dataclass(frozen=True, slots=True)
class SystemConfigDefinition:
    config_key: str
    default_value: str
    value_type: str
    description: str


SYSTEM_CONFIG_DEFINITIONS = [
    SystemConfigDefinition(
        config_key=MAX_RESERVATION_HOURS,
        default_value="4",
        value_type=VALUE_TYPE_INT,
        description="Maximum reservation duration in hours.",
    ),
    SystemConfigDefinition(
        config_key=CHECKIN_GRACE_MINUTES,
        default_value="10",
        value_type=VALUE_TYPE_INT,
        description="Allowed check-in grace period in minutes.",
    ),
    SystemConfigDefinition(
        config_key=VIOLATION_THRESHOLD_MINUTES,
        default_value="15",
        value_type=VALUE_TYPE_INT,
        description="Violation threshold after missed check-in in minutes.",
    ),
]

SYSTEM_CONFIG_DEFINITION_MAP = {
    definition.config_key: definition
    for definition in SYSTEM_CONFIG_DEFINITIONS
}

FIRST_BATCH_CONFIG_KEYS = [definition.config_key for definition in SYSTEM_CONFIG_DEFINITIONS]
