from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserReservationBlock(Base):
    __tablename__ = "user_reservation_blocks"
    __table_args__ = (
        Index(
            "uq_user_reservation_blocks_active_user",
            "user_id",
            unique=True,
            sqlite_where=text("released_at IS NULL"),
            postgresql_where=text("released_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=datetime.now, index=True)
    released_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True, index=True)
