from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, BadRequestError, NotFoundError
from app.modules.identity.models.user import User
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_ADMIN,
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CANCELLED,
    Reservation,
)
from app.modules.reservation.repositories.reservation_repository import ReservationRepository
from app.modules.reservation.schemas.reservation import (
    AdminReservationCancelRequest,
    AdminReservationCreateRequest,
    ReservationWriteData,
    StudentReservationCancelRequest,
    StudentReservationCreateRequest,
)
from app.modules.reservation.services.conflict_service import ConflictService
from app.modules.resource.services.reservation_access_service import ReservationAccessService, ReservableSeatSnapshot
from app.modules.system_config.services.config_reader import ConfigReader
from app.modules.violation.services.violation_service import ViolationService


@dataclass(slots=True)
class ReservationUserSnapshot:
    user_id: int
    department_id: int | None


def build_reservation_write_data(reservation: Reservation) -> ReservationWriteData:
    return ReservationWriteData(
        reservation_id=reservation.id,
        status=reservation.status,
        user_id=reservation.user_id,
        seat_id=reservation.seat_id,
        room_id=reservation.room_id,
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        created_by=reservation.created_by,
        cancelled_by=reservation.cancelled_by,
        cancel_reason=reservation.cancel_reason,
    )


class ReservationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ReservationRepository(session)
        self.conflict_service = ConflictService(session)
        self.config_reader = ConfigReader(session)
        self.resource_access_service = ReservationAccessService(session)
        self.violation_service = ViolationService(session)

    def create_student_reservation(
        self,
        current_student: User,
        payload: StudentReservationCreateRequest,
    ) -> Reservation:
        student = ReservationUserSnapshot(
            user_id=current_student.id,
            department_id=current_student.department_id,
        )
        return self._create_reservation(
            target_user=student,
            seat_id=payload.seat_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            created_by=RESERVATION_SOURCE_STUDENT,
        )

    def create_admin_reservation(self, payload: AdminReservationCreateRequest) -> Reservation:
        target_user = self._load_target_student(payload.user_id)
        return self._create_reservation(
            target_user=target_user,
            seat_id=payload.seat_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            created_by=RESERVATION_SOURCE_ADMIN,
        )

    def cancel_student_reservation(
        self,
        current_student: User,
        reservation_id: int,
        payload: StudentReservationCancelRequest,
    ) -> Reservation:
        reservation = self._get_reservation_or_raise(reservation_id)
        if reservation.user_id != current_student.id:
            raise AuthorizationError("The current user cannot cancel this reservation.")
        self._ensure_booked_status(reservation)
        if datetime.now() >= reservation.start_time:
            raise BadRequestError("Students can only cancel reservations before the start time.")
        reservation.status = RESERVATION_STATUS_CANCELLED
        reservation.cancelled_by = RESERVATION_SOURCE_STUDENT
        reservation.cancel_reason = payload.reason.strip()
        return self.repository.save(reservation)

    def cancel_admin_reservation(
        self,
        reservation_id: int,
        payload: AdminReservationCancelRequest,
    ) -> Reservation:
        reservation = self._get_reservation_or_raise(reservation_id)
        self._ensure_booked_status(reservation)
        reservation.status = RESERVATION_STATUS_CANCELLED
        reservation.cancelled_by = RESERVATION_SOURCE_ADMIN
        reservation.cancel_reason = payload.reason.strip() if payload.reason is not None else None
        return self.repository.save(reservation)

    def _create_reservation(
        self,
        *,
        target_user: ReservationUserSnapshot,
        seat_id: int,
        start_time: datetime,
        end_time: datetime,
        created_by: str,
    ) -> Reservation:
        with self.conflict_service.serialized_reservation_write(user_id=target_user.user_id, seat_id=seat_id):
            try:
                resource = self.resource_access_service.get_reservable_seat_snapshot(
                    seat_id,
                    user_department_id=target_user.department_id,
                )
                self._ensure_user_is_not_penalized(target_user.user_id)
                self._validate_reservation_window(start_time, end_time, resource)
                self.conflict_service.ensure_no_conflict(seat_id, start_time, end_time)
                self.conflict_service.ensure_user_has_no_overlap(target_user.user_id, start_time, end_time)
                reservation = Reservation(
                    user_id=target_user.user_id,
                    seat_id=resource.seat_id,
                    room_id=resource.room_id,
                    start_time=start_time,
                    end_time=end_time,
                    status=RESERVATION_STATUS_BOOKED,
                    created_by=created_by,
                    cancelled_by=None,
                    cancel_reason=None,
                )
                return self.repository.create(reservation)
            except Exception:
                self.session.rollback()
                raise

    def _load_target_student(self, user_id: int) -> ReservationUserSnapshot:
        statement = select(User.id, User.department_id, User.is_active, User.student_no).where(User.id == user_id)
        row = self.session.execute(statement).one_or_none()
        if row is None:
            raise NotFoundError("Student user does not exist.")
        resolved_user_id, department_id, is_active, student_no = row
        if not is_active or not student_no:
            raise NotFoundError("Student user does not exist.")
        return ReservationUserSnapshot(user_id=resolved_user_id, department_id=department_id)

    def _validate_reservation_window(
        self,
        start_time: datetime,
        end_time: datetime,
        resource: ReservableSeatSnapshot,
    ) -> None:
        if start_time >= end_time:
            raise BadRequestError("start_time must be earlier than end_time.")
        if not self._is_on_half_hour_step(start_time) or not self._is_on_half_hour_step(end_time):
            raise BadRequestError("Reservation times must be submitted on 30-minute boundaries.")
        if start_time <= datetime.now():
            raise BadRequestError("Reservation start_time must be in the future.")
        if start_time.date() != end_time.date():
            raise BadRequestError("Reservation must start and end on the same day.")
        duration_hours = (end_time - start_time).total_seconds() / 3600
        if duration_hours > self.config_reader.get_max_reservation_hours():
            raise BadRequestError("Reservation duration exceeds the configured maximum.")
        if start_time.time() < resource.open_time or end_time.time() > resource.close_time:
            raise BadRequestError("Reservation time must be within the study room open hours.")

    def _ensure_user_is_not_penalized(self, user_id: int) -> None:
        penalty_status = self.violation_service.get_user_penalty_status(user_id)
        if penalty_status.is_penalized:
            raise BadRequestError("The target user is currently restricted from creating reservations.")

    def _get_reservation_or_raise(self, reservation_id: int) -> Reservation:
        reservation = self.repository.get_by_id(reservation_id)
        if reservation is None:
            raise NotFoundError("Reservation does not exist.")
        return reservation

    def _ensure_booked_status(self, reservation: Reservation) -> None:
        if reservation.status != RESERVATION_STATUS_BOOKED:
            raise BadRequestError("Only booked reservations can be cancelled.")

    def _is_on_half_hour_step(self, value: datetime) -> bool:
        return value.minute in {0, 30} and value.second == 0 and value.microsecond == 0
