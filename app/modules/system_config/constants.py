from __future__ import annotations

from dataclasses import dataclass

VALUE_TYPE_INT = "int"

MAX_RESERVATION_HOURS = "max_reservation_hours"
CHECKIN_GRACE_MINUTES = "checkin_grace_minutes"
VIOLATION_THRESHOLD_MINUTES = "violation_threshold_minutes"
VIOLATION_PENALTY_THRESHOLD_COUNT = "violation_penalty_threshold_count"
VIOLATION_PENALTY_WINDOW_DAYS = "violation_penalty_window_days"
VIOLATION_PENALTY_DURATION_DAYS = "violation_penalty_duration_days"


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
    SystemConfigDefinition(
        config_key=VIOLATION_PENALTY_THRESHOLD_COUNT,
        default_value="3",
        value_type=VALUE_TYPE_INT,
        description="Violation count required to trigger reservation penalty.",
    ),
    SystemConfigDefinition(
        config_key=VIOLATION_PENALTY_WINDOW_DAYS,
        default_value="30",
        value_type=VALUE_TYPE_INT,
        description="Rolling window in days for violation penalty calculation.",
    ),
    SystemConfigDefinition(
        config_key=VIOLATION_PENALTY_DURATION_DAYS,
        default_value="7",
        value_type=VALUE_TYPE_INT,
        description="Penalty duration in days after violation threshold is reached.",
    ),
]

SYSTEM_CONFIG_DEFINITION_MAP = {
    definition.config_key: definition
    for definition in SYSTEM_CONFIG_DEFINITIONS
}

FIRST_BATCH_CONFIG_KEYS = [definition.config_key for definition in SYSTEM_CONFIG_DEFINITIONS]
