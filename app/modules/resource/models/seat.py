from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.resource.models.study_room import StudyRoom


class Seat(TimestampMixin, Base):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("room_id", "seat_code", name="uq_seats_room_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("study_rooms.id"), nullable=False, index=True)
    seat_code: Mapped[str] = mapped_column(String(50), nullable=False)
    seat_label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_window_side: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_power_socket: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_track_socket: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    room: Mapped["StudyRoom"] = relationship(back_populates="seats")

