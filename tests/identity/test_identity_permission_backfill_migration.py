from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


LEGACY_PERMISSION_CODES = [
    "admin.portal.access",
    "identity.roles.read",
    "identity.roles.write",
    "identity.permissions.read",
    "identity.users.roles.write",
]
BACKFILLED_PERMISSION_CODE = "identity.users.write"
DEPARTMENTS_PERMISSION_CODE = "identity.departments.write"
SYSTEM_ADMIN_ROLE_CODE = "system_admin"
ROOT_DIR = Path(__file__).resolve().parents[2]


def _database_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _make_workspace_database_path(name: str) -> Path:
    return ROOT_DIR / f"{name}_{uuid4().hex}.db"


def _cleanup_database_files(path: Path) -> None:
    for candidate in path.parent.glob(f"{path.name}*"):
        candidate.unlink(missing_ok=True)


def _make_alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _permission_id(connection: sa.Connection, code: str) -> int | None:
    return connection.execute(
        sa.text("SELECT id FROM permissions WHERE code = :code"),
        {"code": code},
    ).scalar_one_or_none()


def _seed_legacy_permissions(
    connection: sa.Connection,
    *,
    include_backfilled_permission: bool,
    include_backfilled_binding: bool,
) -> None:
    for code in LEGACY_PERMISSION_CODES:
        connection.execute(
            sa.text(
                "INSERT INTO permissions (name, code, description) "
                "VALUES (:name, :code, :description)"
            ),
            {
                "name": code,
                "code": code,
                "description": f"legacy permission {code}",
            },
        )

    if include_backfilled_permission:
        connection.execute(
            sa.text(
                "INSERT INTO permissions (name, code, description) "
                "VALUES (:name, :code, :description)"
            ),
            {
                "name": "create users",
                "code": BACKFILLED_PERMISSION_CODE,
                "description": "already backfilled for legacy database",
            },
        )

    connection.execute(
        sa.text(
            "INSERT INTO roles (name, code, description, is_active) "
            "VALUES (:name, :code, :description, :is_active)"
        ),
        {
            "name": "System Admin",
            "code": SYSTEM_ADMIN_ROLE_CODE,
            "description": "legacy system admin role",
            "is_active": True,
        },
    )

    role_id = connection.execute(
        sa.text("SELECT id FROM roles WHERE code = :code"),
        {"code": SYSTEM_ADMIN_ROLE_CODE},
    ).scalar_one()
    for code in LEGACY_PERMISSION_CODES:
        permission_id = _permission_id(connection, code)
        assert permission_id is not None
        connection.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "VALUES (:role_id, :permission_id)"
            ),
            {
                "role_id": role_id,
                "permission_id": permission_id,
            },
        )

    if include_backfilled_binding:
        permission_id = _permission_id(connection, BACKFILLED_PERMISSION_CODE)
        assert permission_id is not None
        connection.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "VALUES (:role_id, :permission_id)"
            ),
            {
                "role_id": role_id,
                "permission_id": permission_id,
            },
        )


@pytest.mark.parametrize(
    ("include_backfilled_permission", "include_backfilled_binding"),
    [
        (False, False),
        (True, False),
        (True, True),
    ],
)
def test_upgrade_backfills_identity_users_write_for_legacy_database(
    monkeypatch: pytest.MonkeyPatch,
    include_backfilled_permission: bool,
    include_backfilled_binding: bool,
) -> None:
    database_path = _make_workspace_database_path("legacy_identity")
    engine: sa.Engine | None = None
    try:
        database_url = _database_url(database_path)
        config = _make_alembic_config(database_url)
        monkeypatch.setenv("DATABASE_URL", database_url)

        command.upgrade(config, "20260420_000001")

        engine = sa.create_engine(database_url, future=True)
        with engine.begin() as connection:
            _seed_legacy_permissions(
                connection,
                include_backfilled_permission=include_backfilled_permission,
                include_backfilled_binding=include_backfilled_binding,
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            for permission_code in (BACKFILLED_PERMISSION_CODE, DEPARTMENTS_PERMISSION_CODE):
                permission_count = connection.execute(
                    sa.text("SELECT COUNT(*) FROM permissions WHERE code = :code"),
                    {"code": permission_code},
                ).scalar_one()
                role_permission_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) "
                        "FROM role_permissions rp "
                        "JOIN roles r ON r.id = rp.role_id "
                        "JOIN permissions p ON p.id = rp.permission_id "
                        "WHERE r.code = :role_code AND p.code = :permission_code"
                    ),
                    {
                        "role_code": SYSTEM_ADMIN_ROLE_CODE,
                        "permission_code": permission_code,
                    },
                ).scalar_one()

                assert permission_count == 1
                assert role_permission_count == 1
    finally:
        if engine is not None:
            engine.dispose()
        _cleanup_database_files(database_path)


def test_upgrade_backfills_permission_definition_without_existing_system_admin_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = _make_workspace_database_path("legacy_without_system_admin")
    engine: sa.Engine | None = None
    try:
        database_url = _database_url(database_path)
        config = _make_alembic_config(database_url)
        monkeypatch.setenv("DATABASE_URL", database_url)

        command.upgrade(config, "20260420_000001")

        engine = sa.create_engine(database_url, future=True)
        with engine.begin() as connection:
            for code in LEGACY_PERMISSION_CODES:
                connection.execute(
                    sa.text(
                        "INSERT INTO permissions (name, code, description) "
                        "VALUES (:name, :code, :description)"
                    ),
                    {
                        "name": code,
                        "code": code,
                        "description": f"legacy permission {code}",
                    },
                )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            for permission_code in (BACKFILLED_PERMISSION_CODE, DEPARTMENTS_PERMISSION_CODE):
                permission_count = connection.execute(
                    sa.text("SELECT COUNT(*) FROM permissions WHERE code = :code"),
                    {"code": permission_code},
                ).scalar_one()
                role_permission_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) "
                        "FROM role_permissions rp "
                        "JOIN permissions p ON p.id = rp.permission_id "
                        "WHERE p.code = :permission_code"
                    ),
                    {"permission_code": permission_code},
                ).scalar_one()

                assert permission_count == 1
                assert role_permission_count == 0
    finally:
        if engine is not None:
            engine.dispose()
        _cleanup_database_files(database_path)
