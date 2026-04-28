from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.identity.models.role import Role
from app.modules.identity.models.user import User
from app.modules.identity.models.user_role import UserRole


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _with_identity_graph(self, stmt):
        return stmt.options(
            selectinload(User.department),
            selectinload(User.user_roles).selectinload(UserRole.role),
        )

    def get_by_student_no(
        self,
        student_no: str,
        *,
        load_relationships: bool = False,
        include_inactive: bool = False,
    ) -> User | None:
        stmt = select(User).where(User.student_no == student_no)
        if not include_inactive:
            stmt = stmt.where(User.is_active.is_(True))
        if load_relationships:
            stmt = self._with_identity_graph(stmt)
        return self.session.scalar(stmt)

    def get_by_email(
        self,
        email: str,
        *,
        load_relationships: bool = False,
        include_inactive: bool = False,
    ) -> User | None:
        stmt = select(User).where(User.email == email)
        if not include_inactive:
            stmt = stmt.where(User.is_active.is_(True))
        if load_relationships:
            stmt = self._with_identity_graph(stmt)
        return self.session.scalar(stmt)

    def get_by_id(
        self,
        user_id: int,
        *,
        load_relationships: bool = False,
        include_inactive: bool = False,
    ) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if not include_inactive:
            stmt = stmt.where(User.is_active.is_(True))
        if load_relationships:
            stmt = self._with_identity_graph(stmt)
        return self.session.scalar(stmt)

    def create_user(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return self.get_by_id(user.id, load_relationships=True, include_inactive=True) or user

    def update_last_login(self, user: User, logged_at: datetime) -> User:
        user.last_login_at = logged_at
        self.session.add(user)
        self.session.commit()
        return user

    def replace_roles(self, user: User, roles: list[Role]) -> User:
        user.user_roles.clear()
        for role in roles:
            user.user_roles.append(UserRole(role=role))
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return self.get_by_id(user.id, load_relationships=True, include_inactive=True) or user
