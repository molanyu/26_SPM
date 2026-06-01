"""add reservation overlap indexes

Revision ID: 20260506_000005
Revises: 20260429_000004
Create Date: 2026-05-06 00:00:05
"""

from __future__ import annotations

from alembic import op


revision = "20260506_000005"
down_revision = "20260429_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_reservations_user_status_time",
        "reservations",
        ["user_id", "status", "start_time", "end_time"],
        unique=False,
    )
    op.create_index(
        "ix_reservations_seat_status_time",
        "reservations",
        ["seat_id", "status", "start_time", "end_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reservations_seat_status_time", table_name="reservations")
    op.drop_index("ix_reservations_user_status_time", table_name="reservations")
