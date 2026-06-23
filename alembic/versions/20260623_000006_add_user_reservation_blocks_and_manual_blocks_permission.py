"""add user reservation blocks and manual block permission

Revision ID: 20260623_000006
Revises: 20260506_000005
Create Date: 2026-06-23 00:00:06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260623_000006"
down_revision = "20260506_000005"
branch_labels = None
depends_on = None


PERMISSION_CODE = "violation.manual_blocks.write"
PERMISSION_NAME = "\u7ef4\u62a4\u624b\u52a8\u9884\u7ea6\u9650\u5236"
PERMISSION_DESCRIPTION = "\u5141\u8bb8\u7ba1\u7406\u5458\u624b\u52a8\u5f00\u542f\u548c\u89e3\u9664\u6307\u5b9a\u7528\u6237\u7684\u9884\u7ea6\u9650\u5236\u3002"
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
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE),
    ).scalar_one_or_none()


def _find_system_admin_role_id(connection: sa.Connection) -> int | None:
    return connection.execute(
        sa.select(roles.c.id).where(roles.c.code == SYSTEM_ADMIN_ROLE_CODE),
    ).scalar_one_or_none()


def upgrade() -> None:
    op.create_table(
        "user_reservation_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("released_by_admin_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_reservation_blocks_user_id", "user_reservation_blocks", ["user_id"], unique=False)
    op.create_index(
        "ix_user_reservation_blocks_created_by_admin_id",
        "user_reservation_blocks",
        ["created_by_admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_reservation_blocks_created_at",
        "user_reservation_blocks",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_reservation_blocks_released_by_admin_id",
        "user_reservation_blocks",
        ["released_by_admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_reservation_blocks_released_at",
        "user_reservation_blocks",
        ["released_at"],
        unique=False,
    )
    op.create_index(
        "uq_user_reservation_blocks_active_user",
        "user_reservation_blocks",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("released_at IS NULL"),
        postgresql_where=sa.text("released_at IS NULL"),
    )

    connection = op.get_bind()
    permission_id = _find_permission_id(connection)
    if permission_id is None:
        connection.execute(
            sa.insert(permissions).values(
                name=PERMISSION_NAME,
                code=PERMISSION_CODE,
                description=PERMISSION_DESCRIPTION,
            ),
        )
        permission_id = _find_permission_id(connection)

    if permission_id is None:
        raise RuntimeError("Failed to backfill violation.manual_blocks.write permission.")

    system_admin_role_id = _find_system_admin_role_id(connection)
    if system_admin_role_id is None:
        return

    existing_binding = connection.execute(
        sa.select(role_permissions.c.id).where(
            role_permissions.c.role_id == system_admin_role_id,
            role_permissions.c.permission_id == permission_id,
        ),
    ).scalar_one_or_none()
    if existing_binding is None:
        connection.execute(
            sa.insert(role_permissions).values(
                role_id=system_admin_role_id,
                permission_id=permission_id,
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()
    permission_id = _find_permission_id(connection)
    if permission_id is not None:
        connection.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == permission_id))
        connection.execute(sa.delete(permissions).where(permissions.c.id == permission_id))

    op.drop_index("uq_user_reservation_blocks_active_user", table_name="user_reservation_blocks")
    op.drop_index("ix_user_reservation_blocks_released_at", table_name="user_reservation_blocks")
    op.drop_index("ix_user_reservation_blocks_released_by_admin_id", table_name="user_reservation_blocks")
    op.drop_index("ix_user_reservation_blocks_created_at", table_name="user_reservation_blocks")
    op.drop_index("ix_user_reservation_blocks_created_by_admin_id", table_name="user_reservation_blocks")
    op.drop_index("ix_user_reservation_blocks_user_id", table_name="user_reservation_blocks")
    op.drop_table("user_reservation_blocks")
