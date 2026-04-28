from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, model_validator

ReservationStatus = Literal["BOOKED", "CHECKED_IN", "CANCELLED", "EXPIRED"]
ReservationSource = Literal["STUDENT", "ADMIN"]


class StudentReservationCreateRequest(BaseModel):
    seat_id: int
    start_time: datetime
    end_time: datetime


class AdminReservationCreateRequest(BaseModel):
    user_id: int
    seat_id: int
    start_time: datetime
    end_time: datetime


class StudentReservationCancelRequest(BaseModel):
    reason: str

    @model_validator(mode="after")
    def validate_reason(self) -> Self:
        if not self.reason.strip():
            raise ValueError("reason must not be blank.")
        return self


class AdminReservationCancelRequest(BaseModel):
    reason: str | None = None

    @model_validator(mode="after")
    def normalize_reason(self) -> Self:
        if self.reason is not None and not self.reason.strip():
            raise ValueError("reason must not be blank when provided.")
        return self


class ReservationWriteData(BaseModel):
    reservation_id: int
    status: ReservationStatus
    user_id: int
    seat_id: int
    room_id: int
    start_time: datetime
    end_time: datetime
    created_by: ReservationSource
    cancelled_by: ReservationSource | None = None
    cancel_reason: str | None = None


class ReservationHistoryItem(BaseModel):
    reservation_id: int
    status: ReservationStatus
    seat_id: int
    room_id: int
    start_time: datetime
    end_time: datetime
    created_by: ReservationSource
    cancelled_by: ReservationSource | None = None
    cancel_reason: str | None = None
