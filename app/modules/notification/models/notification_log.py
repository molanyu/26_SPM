from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

NOTIFICATION_TYPE_RESERVATION_REMINDER = "RESERVATION_REMINDER"
NOTIFICATION_TYPE_NO_SHOW_REMINDER = "NO_SHOW_REMINDER"
NOTIFICATION_TYPE_AUTO_CANCEL_NOTICE = "AUTO_CANCEL_NOTICE"

NOTIFICATION_CHANNEL_MOCK = "MOCK"
NOTIFICATION_CHANNEL_SMTP_EMAIL = "SMTP_EMAIL"

NOTIFICATION_STATUS_PENDING = "PENDING"
NOTIFICATION_STATUS_SENT = "SENT"
NOTIFICATION_STATUS_FAILED = "FAILED"


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "notification_type",
            name="uq_notification_logs_reservation_type",
        ),
        CheckConstraint(
            "notification_type IN ('RESERVATION_REMINDER', 'NO_SHOW_REMINDER', 'AUTO_CANCEL_NOTICE')",
            name="ck_notification_logs_type",
        ),
        CheckConstraint(
            "channel IN ('MOCK', 'SMTP_EMAIL')",
            name="ck_notification_logs_channel",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'SENT', 'FAILED')",
            name="ck_notification_logs_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default=NOTIFICATION_CHANNEL_MOCK)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, index=True)
