from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import timedelta

import jwt

from app.core.config import Settings
from app.core.database import utc_now
from app.core.errors import AuthenticationError

PASSWORD_SCHEME = "pbkdf2_sha256"


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, iterations: int = 390_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{PASSWORD_SCHEME}${iterations}${_urlsafe_b64encode(salt)}${_urlsafe_b64encode(digest)}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        scheme, iteration_text, salt_text, digest_text = stored_hash.split("$", maxsplit=3)
    except ValueError:
        return False
    if scheme != PASSWORD_SCHEME:
        return False
    salt = _urlsafe_b64decode(salt_text)
    expected = _urlsafe_b64decode(digest_text)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iteration_text))
    return hmac.compare_digest(actual, expected)


def create_student_access_token(user_id: int, settings: Settings) -> str:
    payload = {
        "sub": str(user_id),
        "kind": "student_access",
        "exp": utc_now() + timedelta(minutes=settings.student_access_token_ttl_minutes),
        "iat": utc_now(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_student_access_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired student access token.") from exc
    if payload.get("kind") != "student_access":
        raise AuthenticationError("Unsupported access token.")
    return payload


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)
