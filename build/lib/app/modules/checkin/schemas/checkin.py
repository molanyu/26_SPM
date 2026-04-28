from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, model_validator

CheckinMethod = Literal["CODE", "QRCODE"]
CheckinStatus = Literal["CHECKED_IN"]


class StudentCodeCheckinRequest(BaseModel):
    reservation_id: int
    code: str

    @model_validator(mode="after")
    def validate_code(self) -> Self:
        if not self.code.strip():
            raise ValueError("code must not be blank.")
        return self


class StudentQRCodeCheckinRequest(BaseModel):
    reservation_id: int
    token: str

    @model_validator(mode="after")
    def validate_token(self) -> Self:
        if not self.token.strip():
            raise ValueError("token must not be blank.")
        return self


class CheckinSuccessData(BaseModel):
    checkin_record_id: int
    reservation_id: int
    status: CheckinStatus
    room_id: int
    seat_id: int
    checkin_method: CheckinMethod
    checkin_at: datetime
