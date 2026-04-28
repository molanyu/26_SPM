from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CheckinCode(Base):
    __tablename__ = "checkin_codes"
    __table_args__ = (UniqueConstraint("room_id", "code_date", name="uq_checkin_codes_room_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("study_rooms.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    code_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
