from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.modules.resource.services.statistics_query_service import StatisticsQueryService
from app.modules.violation.repositories.statistics_repository import StatisticsRepository
from app.modules.violation.schemas.statistics import (
    RoomUsageStatisticsRead,
    SeatUsageStatisticsRead,
    StatisticsOverviewRead,
    StatisticsQueryFilters,
    UsageStatisticsResponse,
)


class StatisticsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.statistics_repository = StatisticsRepository(session)
        self.resource_statistics_service = StatisticsQueryService(session)

    def get_usage_statistics(self, filters: StatisticsQueryFilters) -> UsageStatisticsResponse:
        context = self.resource_statistics_service.get_room_statistics_context()
        room_ids = [room.room_id for room in context.rooms]
        seat_ids = [seat.seat_id for seat in context.seats]
        window_start, window_end = self._build_window(filters.date_from, filters.date_to)
        day_count = self._count_days(filters.date_from, filters.date_to)

        room_occupied = {
            row.room_id: row.occupied_seconds
            for row in self.statistics_repository.list_room_occupied_durations(
                room_ids=room_ids,
                seat_ids=seat_ids,
                window_start=window_start,
                window_end=window_end,
            )
        }
        seat_occupied = {
            row.seat_id: row.occupied_seconds
            for row in self.statistics_repository.list_seat_occupied_durations(
                seat_ids=seat_ids,
                window_start=window_start,
                window_end=window_end,
            )
        }

        rooms = [
            RoomUsageStatisticsRead(
                room_id=room.room_id,
                room_name=room.room_name,
                usage_rate=self._calculate_rate(
                    numerator=room_occupied.get(room.room_id, 0),
                    denominator=room.open_seconds_per_day * day_count * room.active_seat_count,
                ),
            )
            for room in context.rooms
        ]
        seats = [
            SeatUsageStatisticsRead(
                seat_id=seat.seat_id,
                seat_code=seat.seat_code,
                room_id=seat.room_id,
                usage_rate=self._calculate_rate(
                    numerator=seat_occupied.get(seat.seat_id, 0),
                    denominator=seat.open_seconds_per_day * day_count,
                ),
            )
            for seat in context.seats
        ]

        total_violation_count = self.statistics_repository.count_no_show_violations(
            room_ids=room_ids,
            seat_ids=seat_ids,
            window_start=window_start,
            window_end=window_end,
        )
        violation_denominator = self.statistics_repository.count_violation_denominator(
            room_ids=room_ids,
            seat_ids=seat_ids,
            window_start=window_start,
            window_end=window_end,
        )
        overview = StatisticsOverviewRead(
            total_reserved_minutes=self._seconds_to_minutes(sum(seat_occupied.values())),
            total_violation_count=total_violation_count,
            overall_violation_rate=self._calculate_rate(
                numerator=total_violation_count,
                denominator=violation_denominator,
            ),
        )
        return UsageStatisticsResponse(
            date_from=filters.date_from,
            date_to=filters.date_to,
            overview=overview,
            rooms=rooms,
            seats=seats,
        )

    def _build_window(self, date_from: date, date_to: date) -> tuple[datetime, datetime]:
        start = datetime.combine(date_from, time.min)
        end = datetime.combine(date_to + timedelta(days=1), time.min)
        return start, end

    def _count_days(self, date_from: date, date_to: date) -> int:
        return (date_to - date_from).days + 1

    def _calculate_rate(self, *, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _seconds_to_minutes(self, seconds: int) -> int:
        return seconds // 60
