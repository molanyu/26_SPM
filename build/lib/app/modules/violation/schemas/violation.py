from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, model_validator

ViolationType = Literal["NO_SHOW_TIMEOUT"]


class ViolationQueryFilters(BaseModel):
    user_id: int | None = None
    room_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = 1
    page_size: int = 20

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.page < 1:
            raise ValueError("page must be greater than 0.")
        if self.page_size < 1:
            raise ValueError("page_size must be greater than 0.")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be earlier than or equal to date_to.")
        return self


class ViolationRecordRead(BaseModel):
    violation_id: int
    user_id: int
    reservation_id: int
    room_id: int
    violation_type: ViolationType
    occurred_at: datetime
    remark: str | None = None
    created_at: datetime
