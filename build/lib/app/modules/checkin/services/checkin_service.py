from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.core.errors import AuthorizationError, BadRequestError, ConflictError
from app.modules.checkin.models.checkin_record import CheckinRecord
from app.modules.checkin.repositories.checkin_record_repository import CheckinRecordRepository
from app.modules.checkin.schemas.checkin import StudentCodeCheckinRequest, StudentQRCodeCheckinRequest
from app.modules.checkin.services.code_service import CodeService
from app.modules.identity.models.user import User
from app.modules.reservation.models.reservation import (
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    RESERVATION_STATUS_EXPIRED,
)
from app.modules.reservation.services.checkin_access_service import CheckinReservationService
from app.modules.resource.services.checkin_room_service import CheckinRoomService
from app.modules.system_config.services.config_reader import ConfigReader

CHECKIN_METHOD_CODE = "CODE"
CHECKIN_METHOD_QRCODE = "QRCODE"


@dataclass(slots=True)
class CheckinSuccessSnapshot:
    checkin_record_id: int
    reservation_id: int
    room_id: int
    seat_id: int
    checkin_method: str
    checkin_at: datetime
    status: str


class CheckinService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or load_settings()
        self.config_reader = ConfigReader(session)
        self.record_repository = CheckinRecordRepository(session)
        self.code_service = CodeService(session, self.settings)
        self.reservation_service = CheckinReservationService(session)
        self.room_service = CheckinRoomService(session)

    def check_in_by_code(
        self,
        current_student: User,
        payload: StudentCodeCheckinRequest,
        *,
        now: datetime | None = None,
    ) -> CheckinSuccessSnapshot:
        return self._perform_checkin(
            current_student=current_student,
            reservation_id=payload.reservation_id,
            method=CHECKIN_METHOD_CODE,
            now=now,
            submitted_code=payload.code.strip(),
            token=None,
        )

    def check_in_by_qrcode(
        self,
        current_student: User,
        payload: StudentQRCodeCheckinRequest,
        *,
        now: datetime | None = None,
    ) -> CheckinSuccessSnapshot:
        return self._perform_checkin(
            current_student=current_student,
            reservation_id=payload.reservation_id,
            method=CHECKIN_METHOD_QRCODE,
            now=now,
            submitted_code=None,
            token=payload.token.strip(),
        )

    def _perform_checkin(
        self,
        *,
        current_student: User,
        reservation_id: int,
        method: str,
        now: datetime | None,
        submitted_code: str | None,
        token: str | None,
    ) -> CheckinSuccessSnapshot:
        now = now or datetime.now()
        reservation = self.reservation_service.get_checkin_snapshot(reservation_id)
        if reservation.user_id != current_student.id:
            raise AuthorizationError("The current user cannot check in for this reservation.")
        self._ensure_booked_status(reservation.status)
        if self.record_repository.get_valid_by_reservation_id(reservation_id) is not None:
            raise ConflictError("This reservation has already been checked in.")

        room = self.room_service.get_room_snapshot(reservation.room_id)
        self._validate_checkin_window(reservation.start_time, now)
        expected_code_date = reservation.start_time.date()
        if method == CHECKIN_METHOD_CODE:
            self.code_service.validate_dynamic_code(
                room_id=room.room_id,
                submitted_code=submitted_code or "",
                code_date=expected_code_date,
                now=now,
            )
        else:
            self.code_service.validate_qrcode_token(
                room_id=room.room_id,
                token=token or "",
                code_date=expected_code_date,
                now=now,
            )

        record = CheckinRecord(
            reservation_id=reservation.reservation_id,
            user_id=reservation.user_id,
            room_id=reservation.room_id,
            seat_id=reservation.seat_id,
            checkin_method=method,
            checkin_at=now,
            is_valid=True,
        )
        try:
            self.record_repository.add(record)
            self.session.flush()
            if not self.reservation_service.mark_checked_in(reservation.reservation_id):
                raise BadRequestError("Reservation is not eligible for check-in.")
            self.session.commit()
            self.session.refresh(record)
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("This reservation has already been checked in.") from exc
        except Exception:
            self.session.rollback()
            raise

        return CheckinSuccessSnapshot(
            checkin_record_id=record.id,
            reservation_id=reservation.reservation_id,
            room_id=reservation.room_id,
            seat_id=reservation.seat_id,
            checkin_method=method,
            checkin_at=record.checkin_at,
            status=RESERVATION_STATUS_CHECKED_IN,
        )

    def _ensure_booked_status(self, reservation_status: str) -> None:
        if reservation_status == RESERVATION_STATUS_CANCELLED:
            raise BadRequestError("Cancelled reservations cannot be checked in.")
        if reservation_status == RESERVATION_STATUS_CHECKED_IN:
            raise BadRequestError("This reservation has already been checked in.")
        if reservation_status == RESERVATION_STATUS_EXPIRED:
            raise BadRequestError("Expired reservations cannot be checked in.")
        if reservation_status != RESERVATION_STATUS_BOOKED:
            raise BadRequestError("Reservation is not eligible for check-in.")

    def _validate_checkin_window(self, reservation_start_time: datetime, now: datetime) -> None:
        if now < reservation_start_time:
            raise BadRequestError("Check-in window has not started.")
        grace_minutes = self.config_reader.get_checkin_grace_minutes()
        if now > reservation_start_time + timedelta(minutes=grace_minutes):
            raise BadRequestError("Check-in window has expired.")
