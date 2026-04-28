from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

VIOLATION_TYPE_NO_SHOW_TIMEOUT = "NO_SHOW_TIMEOUT"


class ViolationRecord(Base):
    __tablename__ = "violation_records"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "violation_type",
            name="uq_violation_records_reservation_type",
        ),
        CheckConstraint(
            "violation_type IN ('NO_SHOW_TIMEOUT')",
            name="ck_violation_records_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), nullable=False, index=True)
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, index=True)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=datetime.now)
