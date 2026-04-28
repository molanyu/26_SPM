from __future__ import annotations

from datetime import date as dt_date
from datetime import time as dt_time
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

ResourceSeatStatus = Literal["AVAILABLE"]


class SeatFilterParams(BaseModel):
    date: dt_date | None = None
    start_time: dt_time | None = None
    end_time: dt_time | None = None
    is_window_side: bool | None = None
    has_power_socket: bool | None = None
    has_track_socket: bool | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time.")
        return self


class StudentSeatRead(BaseModel):
    seat_id: int
    seat_code: str
    seat_label: str
    status: ResourceSeatStatus
    is_window_side: bool
    has_power_socket: bool
    has_track_socket: bool


class AdminSeatRead(BaseModel):
    id: int
    room_id: int
    seat_code: str
    seat_label: str
    is_active: bool
    is_window_side: bool
    has_power_socket: bool
    has_track_socket: bool

    model_config = ConfigDict(from_attributes=True)


class SeatCreateRequest(BaseModel):
    room_id: int
    seat_code: str
    seat_label: str
    is_active: bool = True
    is_window_side: bool = False
    has_power_socket: bool = False
    has_track_socket: bool = False


class SeatUpdateRequest(SeatCreateRequest):
    pass
