"""initial schema

Revision ID: 20260420_000001
Revises:
Create Date: 2026-04-20 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260420_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_departments_code", "departments", ["code"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_no", sa.String(length=50), nullable=True, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(student_no IS NOT NULL AND length(trim(student_no)) > 0) OR "
            "(email IS NOT NULL AND length(trim(email)) > 0)",
            name="ck_users_login_identifier_present",
        ),
        sa.CheckConstraint(
            "password_hash IS NOT NULL AND length(trim(password_hash)) > 0",
            name="ck_users_password_hash_present",
        ),
    )
    op.create_index("ix_users_department_id", "users", ["department_id"], unique=False)
    op.create_index("ix_users_student_no", "users", ["student_no"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_table(
        "study_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("is_department_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("open_time", sa.Time(), nullable=False),
        sa.Column("close_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_study_rooms_department_id", "study_rooms", ["department_id"], unique=False)

    op.create_table(
        "seats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("study_rooms.id"), nullable=False),
        sa.Column("seat_code", sa.String(length=50), nullable=False),
        sa.Column("seat_label", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_window_side", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_power_socket", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_track_socket", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("room_id", "seat_code", name="uq_seats_room_code"),
    )
    op.create_index("ix_seats_room_id", "seats", ["room_id"], unique=False)

    op.create_table(
        "system_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_configs_config_key", "system_configs", ["config_key"], unique=False)

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("seat_id", sa.Integer(), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("study_rooms.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.String(length=20), nullable=False),
        sa.Column("cancelled_by", sa.String(length=20), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_time < end_time", name="ck_reservations_time_range"),
        sa.CheckConstraint("status IN ('BOOKED', 'CANCELLED', 'CHECKED_IN', 'EXPIRED')", name="ck_reservations_status"),
        sa.CheckConstraint("created_by IN ('STUDENT', 'ADMIN')", name="ck_reservations_created_by"),
        sa.CheckConstraint(
            "cancelled_by IS NULL OR cancelled_by IN ('STUDENT', 'ADMIN')",
            name="ck_reservations_cancelled_by",
        ),
    )
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"], unique=False)
    op.create_index("ix_reservations_seat_id", "reservations", ["seat_id"], unique=False)
    op.create_index("ix_reservations_room_id", "reservations", ["room_id"], unique=False)
    op.create_index("ix_reservations_start_time", "reservations", ["start_time"], unique=False)
    op.create_index("ix_reservations_end_time", "reservations", ["end_time"], unique=False)
    op.create_index("ix_reservations_status", "reservations", ["status"], unique=False)

    op.create_table(
        "checkin_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("study_rooms.id"), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("code_date", sa.Date(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("room_id", "code_date", name="uq_checkin_codes_room_date"),
    )
    op.create_index("ix_checkin_codes_room_id", "checkin_codes", ["room_id"], unique=False)
    op.create_index("ix_checkin_codes_code_date", "checkin_codes", ["code_date"], unique=False)

    op.create_table(
        "checkin_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reservation_id", sa.Integer(), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("study_rooms.id"), nullable=False),
        sa.Column("seat_id", sa.Integer(), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("checkin_method", sa.String(length=20), nullable=False),
        sa.Column("checkin_at", sa.DateTime(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("reservation_id", name="uq_checkin_records_reservation"),
        sa.CheckConstraint("checkin_method IN ('CODE', 'QRCODE')", name="ck_checkin_records_method"),
    )
    op.create_index("ix_checkin_records_reservation_id", "checkin_records", ["reservation_id"], unique=False)
    op.create_index("ix_checkin_records_user_id", "checkin_records", ["user_id"], unique=False)
    op.create_index("ix_checkin_records_room_id", "checkin_records", ["room_id"], unique=False)
    op.create_index("ix_checkin_records_seat_id", "checkin_records", ["seat_id"], unique=False)
    op.create_index("ix_checkin_records_checkin_at", "checkin_records", ["checkin_at"], unique=False)

    op.create_table(
        "violation_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reservation_id", sa.Integer(), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("violation_type", sa.String(length=50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("reservation_id", "violation_type", name="uq_violation_records_reservation_type"),
        sa.CheckConstraint("violation_type IN ('NO_SHOW_TIMEOUT')", name="ck_violation_records_type"),
    )
    op.create_index("ix_violation_records_user_id", "violation_records", ["user_id"], unique=False)
    op.create_index("ix_violation_records_reservation_id", "violation_records", ["reservation_id"], unique=False)
    op.create_index("ix_violation_records_violation_type", "violation_records", ["violation_type"], unique=False)
    op.create_index("ix_violation_records_occurred_at", "violation_records", ["occurred_at"], unique=False)

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reservation_id", sa.Integer(), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="MOCK"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("reservation_id", "notification_type", name="uq_notification_logs_reservation_type"),
        sa.CheckConstraint(
            "notification_type IN ('RESERVATION_REMINDER', 'NO_SHOW_REMINDER', 'AUTO_CANCEL_NOTICE')",
            name="ck_notification_logs_type",
        ),
        sa.CheckConstraint("channel IN ('MOCK')", name="ck_notification_logs_channel"),
        sa.CheckConstraint("status IN ('PENDING', 'SENT', 'FAILED')", name="ck_notification_logs_status"),
    )
    op.create_index("ix_notification_logs_user_id", "notification_logs", ["user_id"], unique=False)
    op.create_index("ix_notification_logs_reservation_id", "notification_logs", ["reservation_id"], unique=False)
    op.create_index("ix_notification_logs_notification_type", "notification_logs", ["notification_type"], unique=False)
    op.create_index("ix_notification_logs_status", "notification_logs", ["status"], unique=False)
    op.create_index("ix_notification_logs_sent_at", "notification_logs", ["sent_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notification_logs_sent_at", table_name="notification_logs")
    op.drop_index("ix_notification_logs_status", table_name="notification_logs")
    op.drop_index("ix_notification_logs_notification_type", table_name="notification_logs")
    op.drop_index("ix_notification_logs_reservation_id", table_name="notification_logs")
    op.drop_index("ix_notification_logs_user_id", table_name="notification_logs")
    op.drop_table("notification_logs")

    op.drop_index("ix_violation_records_occurred_at", table_name="violation_records")
    op.drop_index("ix_violation_records_violation_type", table_name="violation_records")
    op.drop_index("ix_violation_records_reservation_id", table_name="violation_records")
    op.drop_index("ix_violation_records_user_id", table_name="violation_records")
    op.drop_table("violation_records")

    op.drop_index("ix_checkin_records_checkin_at", table_name="checkin_records")
    op.drop_index("ix_checkin_records_seat_id", table_name="checkin_records")
    op.drop_index("ix_checkin_records_room_id", table_name="checkin_records")
    op.drop_index("ix_checkin_records_user_id", table_name="checkin_records")
    op.drop_index("ix_checkin_records_reservation_id", table_name="checkin_records")
    op.drop_table("checkin_records")

    op.drop_index("ix_checkin_codes_code_date", table_name="checkin_codes")
    op.drop_index("ix_checkin_codes_room_id", table_name="checkin_codes")
    op.drop_table("checkin_codes")

    op.drop_index("ix_reservations_status", table_name="reservations")
    op.drop_index("ix_reservations_end_time", table_name="reservations")
    op.drop_index("ix_reservations_start_time", table_name="reservations")
    op.drop_index("ix_reservations_room_id", table_name="reservations")
    op.drop_index("ix_reservations_seat_id", table_name="reservations")
    op.drop_index("ix_reservations_user_id", table_name="reservations")
    op.drop_table("reservations")

    op.drop_index("ix_system_configs_config_key", table_name="system_configs")
    op.drop_table("system_configs")

    op.drop_index("ix_seats_room_id", table_name="seats")
    op.drop_table("seats")

    op.drop_index("ix_study_rooms_department_id", table_name="study_rooms")
    op.drop_table("study_rooms")

    op.drop_table("user_roles")
    op.drop_table("role_permissions")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_student_no", table_name="users")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_departments_code", table_name="departments")
    op.drop_table("departments")
