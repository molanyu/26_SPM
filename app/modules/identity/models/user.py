from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.identity.models.department import Department
    from app.modules.identity.models.user_role import UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(student_no IS NOT NULL AND length(trim(student_no)) > 0) OR "
            "(email IS NOT NULL AND length(trim(email)) > 0)",
            name="ck_users_login_identifier_present",
        ),
        CheckConstraint(
            "password_hash IS NOT NULL AND length(trim(password_hash)) > 0",
            name="ck_users_password_hash_present",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_no: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None]

    department: Mapped["Department | None"] = relationship(back_populates="users")
    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @validates("student_no", "email")
    def normalize_login_identifier(self, _: str, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @validates("password_hash")
    def validate_password_hash(self, _: str, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("password_hash cannot be blank.")
        return cleaned
