from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac

import jwt

from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.core.errors import BadRequestError
from app.modules.resource.services.checkin_room_service import CheckinRoomService

CHECKIN_CODE_WINDOW_MINUTES = 5


@dataclass(slots=True)
class DynamicCheckinCode:
    room_id: int
    code: str
    time_slice_start: datetime
    expires_at: datetime
    remaining_seconds: int


@dataclass(slots=True)
class QRCodePayload:
    room_id: int
    time_slice_start: datetime
    code: str
    expires_at: datetime


class CodeService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or load_settings()
        self.room_service = CheckinRoomService(session)

    def get_current_dynamic_code(self, room_id: int, *, now: datetime | None = None) -> DynamicCheckinCode:
        self.room_service.get_active_room_snapshot(room_id)
        resolved_now = now or datetime.now()
        time_slice_start = self._time_slice_start(resolved_now)
        expires_at = time_slice_start + timedelta(minutes=CHECKIN_CODE_WINDOW_MINUTES)
        remaining_seconds = max(0, int((expires_at - resolved_now).total_seconds()))
        return DynamicCheckinCode(
            room_id=room_id,
            code=self._derive_code(room_id, time_slice_start),
            time_slice_start=time_slice_start,
            expires_at=expires_at,
            remaining_seconds=remaining_seconds,
        )

    def get_current_dynamic_codes(self, *, now: datetime | None = None) -> list[DynamicCheckinCode]:
        return [
            self.get_current_dynamic_code(room.room_id, now=now)
            for room in self.room_service.list_active_room_snapshots()
        ]

    def validate_dynamic_code(
        self,
        *,
        room_id: int,
        submitted_code: str,
        now: datetime | None = None,
    ) -> DynamicCheckinCode:
        current_code = self.get_current_dynamic_code(room_id, now=now)
        if not hmac.compare_digest(current_code.code, submitted_code.strip()):
            raise BadRequestError("Invalid or expired check-in code.", code="invalid_checkin_code")
        return current_code

    def generate_qrcode_token(
        self,
        *,
        room_id: int,
        now: datetime | None = None,
    ) -> str:
        current_code = self.get_current_dynamic_code(room_id, now=now)
        issued_at = int((now or datetime.now()).timestamp())
        payload = {
            "kind": "checkin_qrcode",
            "room_id": room_id,
            "time_slice_start": current_code.time_slice_start.isoformat(),
            "code": current_code.code,
            "iat": issued_at,
            "exp": int(current_code.expires_at.timestamp()),
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def validate_qrcode_token(
        self,
        *,
        room_id: int,
        token: str,
        now: datetime | None = None,
    ) -> DynamicCheckinCode:
        payload = self._decode_qrcode_token(token)
        resolved_now = now or datetime.now()
        if payload.room_id != room_id:
            raise BadRequestError("QR code does not match the reservation room.", code="invalid_qrcode")
        if payload.expires_at <= resolved_now:
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode")
        current_code = self.get_current_dynamic_code(room_id, now=resolved_now)
        if payload.time_slice_start != current_code.time_slice_start:
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode")
        if not hmac.compare_digest(payload.code, current_code.code):
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode")
        return current_code

    def _decode_qrcode_token(self, token: str) -> QRCodePayload:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError as exc:
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode") from exc
        if payload.get("kind") != "checkin_qrcode":
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode")
        try:
            return QRCodePayload(
                room_id=int(payload["room_id"]),
                time_slice_start=datetime.fromisoformat(str(payload["time_slice_start"])),
                code=str(payload["code"]),
                expires_at=datetime.fromtimestamp(int(payload["exp"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode") from exc

    def _time_slice_start(self, value: datetime) -> datetime:
        slice_minute = (value.minute // CHECKIN_CODE_WINDOW_MINUTES) * CHECKIN_CODE_WINDOW_MINUTES
        return value.replace(minute=slice_minute, second=0, microsecond=0)

    def _derive_code(self, room_id: int, time_slice_start: datetime) -> str:
        message = f"checkin:{room_id}:{time_slice_start.isoformat(timespec='minutes')}".encode("utf-8")
        digest = hmac.new(
            self.settings.jwt_secret_key.encode("utf-8"),
            message,
            hashlib.sha256,
        ).digest()
        return f"{int.from_bytes(digest[:8], 'big') % 1_000_000:06d}"
