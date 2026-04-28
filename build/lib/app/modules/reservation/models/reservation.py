from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

RESERVATION_STATUS_BOOKED = "BOOKED"
RESERVATION_STATUS_CANCELLED = "CANCELLED"
RESERVATION_STATUS_CHECKED_IN = "CHECKED_IN"
RESERVATION_STATUS_EXPIRED = "EXPIRED"

RESERVATION_SOURCE_STUDENT = "STUDENT"
RESERVATION_SOURCE_ADMIN = "ADMIN"


class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_reservations_time_range"),
        CheckConstraint(
            "status IN ('BOOKED', 'CANCELLED', 'CHECKED_IN', 'EXPIRED')",
            name="ck_reservations_status",
        ),
        CheckConstraint(
            "created_by IN ('STUDENT', 'ADMIN')",
            name="ck_reservations_created_by",
        ),
        CheckConstraint(
            "cancelled_by IS NULL OR cancelled_by IN ('STUDENT', 'ADMIN')",
            name="ck_reservations_cancelled_by",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), nullable=False, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("study_rooms.id"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(20), nullable=False)
    cancelled_by: Mapped[str | None] = mapped_column(String(20))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
