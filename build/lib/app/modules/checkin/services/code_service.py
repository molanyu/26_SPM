from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import secrets

import jwt

from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.core.errors import BadRequestError
from app.modules.checkin.models.checkin_code import CheckinCode
from app.modules.checkin.repositories.checkin_code_repository import CheckinCodeRepository
from app.modules.resource.services.checkin_room_service import CheckinRoomService


@dataclass(slots=True)
class QRCodePayload:
    room_id: int
    code_date: date
    code: str


class CodeService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or load_settings()
        self.repository = CheckinCodeRepository(session)
        self.room_service = CheckinRoomService(session)

    def ensure_daily_code(self, room_id: int, *, code_date: date, now: datetime | None = None) -> CheckinCode:
        self.room_service.get_active_room_snapshot(room_id)
        existing = self.repository.get_by_room_and_date(room_id, code_date)
        if existing is not None:
            return existing

        created_at = now or datetime.now()
        expires_at = datetime.combine(code_date + timedelta(days=1), time.min)
        checkin_code = CheckinCode(
            room_id=room_id,
            code=self._generate_code(),
            code_date=code_date,
            expires_at=expires_at,
            created_at=created_at,
        )
        self.repository.add(checkin_code)
        self.session.commit()
        self.session.refresh(checkin_code)
        return checkin_code

    def ensure_daily_codes(self, *, code_date: date, now: datetime | None = None) -> list[CheckinCode]:
        return [
            self.ensure_daily_code(room.room_id, code_date=code_date, now=now)
            for room in self.room_service.list_active_room_snapshots()
        ]

    def validate_dynamic_code(
        self,
        *,
        room_id: int,
        submitted_code: str,
        code_date: date,
        now: datetime | None = None,
    ) -> CheckinCode:
        record = self.repository.get_by_room_and_date(room_id, code_date)
        now = now or datetime.now()
        if record is None or record.expires_at <= now or record.code != submitted_code.strip():
            raise BadRequestError("Invalid or expired check-in code.", code="invalid_checkin_code")
        return record

    def generate_qrcode_token(self, *, room_id: int, code_date: date, now: datetime | None = None) -> str:
        record = self.ensure_daily_code(room_id, code_date=code_date, now=now)
        issued_at = int((now or datetime.now()).timestamp())
        payload = {
            "kind": "checkin_qrcode",
            "room_id": room_id,
            "code_date": code_date.isoformat(),
            "code": record.code,
            "iat": issued_at,
            "exp": int(record.expires_at.timestamp()),
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def validate_qrcode_token(
        self,
        *,
        room_id: int,
        token: str,
        code_date: date,
        now: datetime | None = None,
    ) -> CheckinCode:
        payload = self._decode_qrcode_token(token)
        if payload.room_id != room_id or payload.code_date != code_date:
            raise BadRequestError("QR code does not match the reservation room.", code="invalid_qrcode")
        return self.validate_dynamic_code(
            room_id=room_id,
            submitted_code=payload.code,
            code_date=payload.code_date,
            now=now,
        )

    def _decode_qrcode_token(self, token: str) -> QRCodePayload:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
        except jwt.InvalidTokenError as exc:
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode") from exc
        if payload.get("kind") != "checkin_qrcode":
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode")
        try:
            return QRCodePayload(
                room_id=int(payload["room_id"]),
                code_date=date.fromisoformat(str(payload["code_date"])),
                code=str(payload["code"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestError("Invalid or expired QR code.", code="invalid_qrcode") from exc

    def _generate_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"
