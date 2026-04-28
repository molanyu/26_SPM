from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.reservation.schemas.reservation import ReservationStatus

AssistantIntent = Literal[
    "QUERY_AVAILABLE_SEATS",
    "QUERY_WINDOW_SEATS",
    "QUERY_TODAY_MY_RESERVATION",
]
AssistantSeatAttribute = Literal["WINDOW", "POWER_SOCKET", "TRACK_SOCKET"]
AssistantResultType = Literal[
    "AVAILABLE_SEAT_LIST",
    "SEAT_ATTRIBUTE_LIST",
    "TODAY_MY_RESERVATION",
    "CONTROLLED_FAILURE",
]
AssistantFailureCode = Literal["INTENT_NOT_RECOGNIZED", "QUERY_EXECUTION_FAILED"]


class AssistantQueryRequest(BaseModel):
    message: str

    @model_validator(mode="after")
    def validate_message(self) -> "AssistantQueryRequest":
        if not self.message.strip():
            raise ValueError("message must not be blank.")
        return self


class AssistantAvailableSeatItem(BaseModel):
    seat_id: int
    seat_code: str
    seat_label: str
    room_id: int
    room_name: str
    available_time_range: str


class AssistantSeatAttributeItem(BaseModel):
    seat_id: int
    seat_code: str
    seat_label: str
    room_id: int
    room_name: str
    is_window_side: bool
    has_power_socket: bool
    has_track_socket: bool


class AssistantTodayReservationItem(BaseModel):
    reservation_id: int
    status: ReservationStatus
    seat_id: int
    room_id: int
    room_name: str | None = None
    start_time: datetime
    end_time: datetime


class AssistantAvailableSeatsResult(BaseModel):
    query_date: dt_date
    query_window: str
    items: list[AssistantAvailableSeatItem] = Field(default_factory=list)


class AssistantSeatAttributeQueryResult(BaseModel):
    requested_attribute: AssistantSeatAttribute
    items: list[AssistantSeatAttributeItem] = Field(default_factory=list)


class AssistantTodayMyReservationResult(BaseModel):
    query_date: dt_date
    items: list[AssistantTodayReservationItem] = Field(default_factory=list)


class AssistantControlledFailureResult(BaseModel):
    code: AssistantFailureCode
    message: str


class AssistantQueryResponse(BaseModel):
    intent: AssistantIntent | None
    result_type: AssistantResultType
    result: dict[str, Any]

