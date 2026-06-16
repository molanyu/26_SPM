from __future__ import annotations

from datetime import date, datetime
from datetime import time as dt_time
from typing import Literal, Self

from pydantic import BaseModel, model_validator

ReservationStatus = Literal["BOOKED", "CHECKED_IN", "CANCELLED", "EXPIRED"]
ReservationSource = Literal["STUDENT", "ADMIN"]
SeatAvailabilityStatus = Literal["AVAILABLE", "OCCUPIED"]


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


class AdminReservationQueryFilters(BaseModel):
    user_id: int | None = None
    room_id: int | None = None
    seat_id: int | None = None
    status: ReservationStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = 1
    page_size: int = 20

    @model_validator(mode="after")
    def validate_filters(self) -> Self:
        if self.page < 1:
            raise ValueError("page must be greater than 0.")
        if self.page_size < 1:
            raise ValueError("page_size must be greater than 0.")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be earlier than or equal to date_to.")
        return self


class SeatAvailabilityQueryParams(BaseModel):
    date: date
    start_time: dt_time
    end_time: dt_time
    is_window_side: bool | None = None
    has_power_socket: bool | None = None
    has_track_socket: bool | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time.")
        return self


class SeatAvailabilityRead(BaseModel):
    seat_id: int
    seat_code: str
    seat_label: str
    status: SeatAvailabilityStatus
    is_window_side: bool
    has_power_socket: bool
    has_track_socket: bool
