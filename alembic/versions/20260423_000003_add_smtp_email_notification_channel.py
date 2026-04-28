"""add smtp email notification channel

Revision ID: 20260423_000003
Revises: 20260421_000002
Create Date: 2026-04-23 00:00:03
"""

from __future__ import annotations

from alembic import op


revision = "20260423_000003"
down_revision = "20260421_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notification_logs") as batch_op:
        batch_op.drop_constraint("ck_notification_logs_channel", type_="check")
        batch_op.create_check_constraint(
            "ck_notification_logs_channel",
            "channel IN ('MOCK', 'SMTP_EMAIL')",
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_logs") as batch_op:
        batch_op.drop_constraint("ck_notification_logs_channel", type_="check")
        batch_op.create_check_constraint(
            "ck_notification_logs_channel",
            "channel IN ('MOCK')",
        )
