from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.identity.models.user import User


def test_user_requires_non_blank_password_hash(client) -> None:
    with pytest.raises(ValueError):
        User(
            student_no="20249999",
            name="Invalid Password User",
            password_hash="   ",
            is_active=True,
        )


def test_user_requires_login_identifier(client) -> None:
    with SessionLocal() as session:
        user = User(
            name="Missing Identifier User",
            password_hash=hash_password("valid-password"),
            is_active=True,
        )
        session.add(user)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
