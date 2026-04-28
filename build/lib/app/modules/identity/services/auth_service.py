from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import utc_now
from app.core.errors import AuthenticationError
from app.core.security import (
    create_student_access_token,
    decode_student_access_token,
    generate_session_token,
    verify_password,
)
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.models.user import User
from app.modules.identity.repositories.permission_repository import PermissionRepository
from app.modules.identity.repositories.user_repository import UserRepository


@dataclass(slots=True)
class AdminSessionRecord:
    user_id: int
    expires_at: datetime


class AdminSessionStore:
    def __init__(self, ttl_minutes: int) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict[str, AdminSessionRecord] = {}
        self._lock = Lock()

    def create(self, user_id: int) -> str:
        token = generate_session_token()
        with self._lock:
            self._sessions[token] = AdminSessionRecord(
                user_id=user_id,
                expires_at=utc_now() + self._ttl,
            )
        return token

    def resolve(self, token: str | None) -> int | None:
        if not token:
            return None
        with self._lock:
            record = self._sessions.get(token)
            if record is None:
                return None
            if record.expires_at <= utc_now():
                self._sessions.pop(token, None)
                return None
            return record.user_id

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)


class AuthService:
    def __init__(self, session: Session, settings: Settings, session_store: AdminSessionStore) -> None:
        self.session = session
        self.settings = settings
        self.session_store = session_store
        self.user_repository = UserRepository(session)
        self.permission_repository = PermissionRepository(session)

    def login_student(self, student_no: str, password: str) -> tuple[str, User]:
        user = self.user_repository.get_by_student_no(student_no, load_relationships=True)
        if user is None or not user.is_active or not user.student_no:
            raise AuthenticationError("Student number or password is incorrect.")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Student number or password is incorrect.")
        self.user_repository.update_last_login(user, utc_now())
        token = create_student_access_token(user.id, self.settings)
        return token, user

    def get_student_from_token(self, token: str | None) -> User:
        if not token:
            raise AuthenticationError("Missing student access token.")
        payload = decode_student_access_token(token, self.settings)
        user_id = int(str(payload["sub"]))
        user = self.user_repository.get_by_id(user_id, load_relationships=True)
        if user is None or not user.student_no:
            raise AuthenticationError("Student identity is invalid.")
        return user

    def login_admin(self, email: str, password: str) -> tuple[str, User]:
        user = self.user_repository.get_by_email(email, load_relationships=True)
        if user is None or not user.is_active or not user.email:
            raise AuthenticationError("Email or password is incorrect.")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Email or password is incorrect.")
        if not self.permission_repository.user_has_permission(user.id, ADMIN_PORTAL_ACCESS):
            raise AuthenticationError("This user is not allowed to access the admin portal.")
        self.user_repository.update_last_login(user, utc_now())
        session_token = self.session_store.create(user.id)
        return session_token, user

    def get_admin_from_session(self, session_token: str | None) -> User:
        user_id = self.session_store.resolve(session_token)
        if user_id is None:
            raise AuthenticationError("Missing or expired admin session.")
        user = self.user_repository.get_by_id(user_id, load_relationships=True)
        if user is None or not user.email:
            raise AuthenticationError("Admin session is no longer valid.")
        if not self.permission_repository.user_has_permission(user.id, ADMIN_PORTAL_ACCESS):
            raise AuthenticationError("Admin access has been revoked.")
        return user

    def logout_admin(self, session_token: str | None) -> None:
        self.session_store.revoke(session_token)

