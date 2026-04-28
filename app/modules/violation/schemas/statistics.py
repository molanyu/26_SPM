from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, model_validator


class StatisticsQueryFilters(BaseModel):
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.date_from > self.date_to:
            raise ValueError("date_from must be earlier than or equal to date_to.")
        return self


class StatisticsOverviewRead(BaseModel):
    total_reserved_minutes: int
    total_violation_count: int
    overall_violation_rate: float


class RoomUsageStatisticsRead(BaseModel):
    room_id: int
    room_name: str
    usage_rate: float


class SeatUsageStatisticsRead(BaseModel):
    seat_id: int
    seat_code: str
    room_id: int
    usage_rate: float


class UsageStatisticsResponse(BaseModel):
    date_from: date
    date_to: date
    overview: StatisticsOverviewRead
    rooms: list[RoomUsageStatisticsRead]
    seats: list[SeatUsageStatisticsRead]
