from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    app_name: str = "SPM Identity API"
    database_url: str = "sqlite:///./spm_identity.db"
    database_auto_create: bool = True
    jwt_secret_key: str = "spm-dev-secret"
    jwt_algorithm: str = "HS256"
    student_access_token_ttl_minutes: int = 60
    admin_session_ttl_minutes: int = 480
    admin_session_cookie_name: str = "spm_admin_session"
    admin_session_cookie_secure: bool = False
    admin_session_cookie_samesite: str = "lax"
    identity_bootstrap_enabled: bool = False
    identity_bootstrap_admin_email: str | None = None
    identity_bootstrap_admin_name: str = "System Admin"
    identity_bootstrap_admin_password: str | None = None
    notification_default_channel: str = "mock"
    smtp_host: str | None = None
    smtp_port: str | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: str = "10"
    task_scheduler_enabled: bool = False
    task_scheduler_interval_seconds: int = 60


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "SPM Identity API"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./spm_identity.db"),
        database_auto_create=_read_bool("DATABASE_AUTO_CREATE", True),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "spm-dev-secret"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        student_access_token_ttl_minutes=int(os.getenv("STUDENT_ACCESS_TOKEN_TTL_MINUTES", "60")),
        admin_session_ttl_minutes=int(os.getenv("ADMIN_SESSION_TTL_MINUTES", "480")),
        admin_session_cookie_name=os.getenv("ADMIN_SESSION_COOKIE_NAME", "spm_admin_session"),
        admin_session_cookie_secure=_read_bool("ADMIN_SESSION_COOKIE_SECURE", False),
        admin_session_cookie_samesite=os.getenv("ADMIN_SESSION_COOKIE_SAMESITE", "lax"),
        identity_bootstrap_enabled=_read_bool("IDENTITY_BOOTSTRAP_ENABLED", False),
        identity_bootstrap_admin_email=os.getenv("IDENTITY_BOOTSTRAP_ADMIN_EMAIL"),
        identity_bootstrap_admin_name=os.getenv("IDENTITY_BOOTSTRAP_ADMIN_NAME", "System Admin"),
        identity_bootstrap_admin_password=os.getenv("IDENTITY_BOOTSTRAP_ADMIN_PASSWORD"),
        notification_default_channel=os.getenv("NOTIFICATION_DEFAULT_CHANNEL", "mock"),
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=os.getenv("SMTP_PORT"),
        smtp_username=os.getenv("SMTP_USERNAME"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        smtp_from_email=os.getenv("SMTP_FROM_EMAIL"),
        smtp_use_tls=_read_bool("SMTP_USE_TLS", True),
        smtp_timeout_seconds=os.getenv("SMTP_TIMEOUT_SECONDS", "10"),
        task_scheduler_enabled=_read_bool("TASK_SCHEDULER_ENABLED", False),
        task_scheduler_interval_seconds=int(os.getenv("TASK_SCHEDULER_INTERVAL_SECONDS", "60")),
    )
