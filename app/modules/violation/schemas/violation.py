from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, model_validator

ViolationType = Literal["NO_SHOW_TIMEOUT"]


class ViolationQueryFilters(BaseModel):
    user_id: int | None = None
    student_no: str | None = None
    room_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = 1
    page_size: int = 20

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.page < 1:
            raise ValueError("页码必须大于 0。")
        if self.page_size < 1:
            raise ValueError("每页条数必须大于 0。")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期。")
        if self.student_no is not None:
            self.student_no = self.student_no.strip() or None
        return self


class ViolationRecordRead(BaseModel):
    violation_id: int
    user_id: int
    student_no: str | None = None
    reservation_id: int
    room_id: int
    violation_type: ViolationType
    occurred_at: datetime
    remark: str | None = None
    created_at: datetime


class UserPenaltyStatusRead(BaseModel):
    is_penalized: bool
    violation_count: int
    window_start: datetime
    window_end: datetime
    penalty_start: datetime | None = None
    penalty_end: datetime | None = None
