"""backfill identity.departments.write for legacy databases

Revision ID: 20260429_000004
Revises: 20260423_000003
Create Date: 2026-04-29 00:00:04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260429_000004"
down_revision = "20260423_000003"
branch_labels = None
depends_on = None


PERMISSION_CODE = "identity.departments.write"
PERMISSION_NAME = "\u7ef4\u62a4\u9662\u7cfb"
PERMISSION_DESCRIPTION = "\u5141\u8bb8\u67e5\u770b\u3001\u65b0\u589e\u3001\u542f\u7528\u548c\u505c\u7528\u9662\u7cfb\u3002"
SYSTEM_ADMIN_ROLE_CODE = "system_admin"

permissions = sa.table(
    "permissions",
    sa.column("id", sa.Integer()),
    sa.column("name", sa.String(length=100)),
    sa.column("code", sa.String(length=100)),
    sa.column("description", sa.Text()),
)

roles = sa.table(
    "roles",
    sa.column("id", sa.Integer()),
    sa.column("code", sa.String(length=100)),
)

role_permissions = sa.table(
    "role_permissions",
    sa.column("id", sa.Integer()),
    sa.column("role_id", sa.Integer()),
    sa.column("permission_id", sa.Integer()),
)


def _find_permission_id(connection: sa.Connection) -> int | None:
    return connection.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar_one_or_none()


def _find_system_admin_role_id(connection: sa.Connection) -> int | None:
    return connection.execute(
        sa.select(roles.c.id).where(roles.c.code == SYSTEM_ADMIN_ROLE_CODE)
    ).scalar_one_or_none()


def upgrade() -> None:
    connection = op.get_bind()

    permission_id = _find_permission_id(connection)
    if permission_id is None:
        connection.execute(
            sa.insert(permissions).values(
                name=PERMISSION_NAME,
                code=PERMISSION_CODE,
                description=PERMISSION_DESCRIPTION,
            )
        )
        permission_id = _find_permission_id(connection)

    if permission_id is None:
        raise RuntimeError("Failed to backfill identity.departments.write permission.")

    system_admin_role_id = _find_system_admin_role_id(connection)
    if system_admin_role_id is None:
        return

    existing_binding = connection.execute(
        sa.select(role_permissions.c.id).where(
            role_permissions.c.role_id == system_admin_role_id,
            role_permissions.c.permission_id == permission_id,
        )
    ).scalar_one_or_none()
    if existing_binding is None:
        connection.execute(
            sa.insert(role_permissions).values(
                role_id=system_admin_role_id,
                permission_id=permission_id,
            )
        )


def downgrade() -> None:
    connection = op.get_bind()
    permission_id = _find_permission_id(connection)
    if permission_id is None:
        return

    connection.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == permission_id))
    connection.execute(sa.delete(permissions).where(permissions.c.id == permission_id))
