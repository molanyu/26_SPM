from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class CheckinRecord(TimestampMixin, Base):
    __tablename__ = "checkin_records"
    __table_args__ = (
        UniqueConstraint("reservation_id", name="uq_checkin_records_reservation"),
        CheckConstraint(
            "checkin_method IN ('CODE', 'QRCODE')",
            name="ck_checkin_records_method",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("study_rooms.id"), nullable=False, index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), nullable=False, index=True)
    checkin_method: Mapped[str] = mapped_column(String(20), nullable=False)
    checkin_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, index=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
