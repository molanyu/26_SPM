from __future__ import annotations

from dataclasses import dataclass
from datetime import date as dt_date
from datetime import datetime
from datetime import time as dt_time
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.assistant.schemas.query import (
    AssistantAvailableSeatItem,
    AssistantAvailableSeatsResult,
    AssistantControlledFailureResult,
    AssistantQueryResponse,
    AssistantSeatAttribute,
    AssistantSeatAttributeItem,
    AssistantSeatAttributeQueryResult,
    AssistantTodayMyReservationResult,
    AssistantTodayReservationItem,
)
from app.modules.assistant.services.intent_service import IntentParseResult, IntentService
from app.modules.reservation.services.assistant_access_service import AssistantReservationService
from app.modules.reservation.services.history_service import HistoryService
from app.modules.resource.schemas.seat import SeatFilterParams
from app.modules.resource.services.room_service import RoomService
from app.modules.resource.services.seat_service import SeatService

_ROOM_PAGE_SIZE = 100
_RESERVATION_PAGE_SIZE = 100
_EVENING_START_TIME = dt_time(hour=18, minute=0)


class StudentContext(Protocol):
    id: int
    department_id: int | None


@dataclass(slots=True)
class VisibleRoomSnapshot:
    room_id: int
    room_name: str
    open_time: dt_time
    close_time: dt_time


class AssistantQueryService:
    def __init__(self, session: Session) -> None:
        self.intent_service = IntentService()
        self.room_service = RoomService(session)
        self.seat_service = SeatService(session)
        self.history_service = HistoryService(session)
        self.assistant_reservation_service = AssistantReservationService(session)

    def query(self, current_student: StudentContext, message: str) -> AssistantQueryResponse:
        parsed_intent = self.intent_service.parse_message(message)
        if parsed_intent.intent is None:
            return self._build_controlled_failure(
                intent=None,
                code="INTENT_NOT_RECOGNIZED",
                message="The assistant could not recognize this query.",
            )
        try:
            if parsed_intent.intent == "QUERY_AVAILABLE_SEATS":
                return self._query_available_seats(current_student)
            if parsed_intent.intent == "QUERY_WINDOW_SEATS":
                return self._query_seat_attributes(current_student, parsed_intent)
            return self._query_today_my_reservation(current_student)
        except AppError:
            return self._build_controlled_failure(
                intent=parsed_intent.intent,
                code="QUERY_EXECUTION_FAILED",
                message="The assistant could not complete this query.",
            )
        except Exception:
            return self._build_controlled_failure(
                intent=parsed_intent.intent,
                code="QUERY_EXECUTION_FAILED",
                message="The assistant could not complete this query.",
            )

    def _query_available_seats(self, current_student: StudentContext) -> AssistantQueryResponse:
        today = dt_date.today()
        items: list[AssistantAvailableSeatItem] = []
        for room in self._list_visible_rooms(current_student):
            tonight_window = self._resolve_tonight_window(today, room.open_time, room.close_time)
            if tonight_window is None:
                continue
            start_time, end_time = tonight_window
            occupied_seat_ids = self._list_occupied_seat_ids(
                room.room_id,
                start_time=start_time,
                end_time=end_time,
            )
            seat_payload = self.seat_service.list_student_seats(current_student, room.room_id, SeatFilterParams())
            for seat in seat_payload["items"]:
                if seat["seat_id"] in occupied_seat_ids:
                    continue
                items.append(
                    AssistantAvailableSeatItem(
                        seat_id=seat["seat_id"],
                        seat_code=seat["seat_code"],
                        seat_label=seat["seat_label"],
                        room_id=room.room_id,
                        room_name=room.room_name,
                        available_time_range=self._format_time_range(start_time.time(), end_time.time()),
                    ),
                )
        result = AssistantAvailableSeatsResult(
            query_date=today,
            query_window="TONIGHT",
            items=items,
        )
        return AssistantQueryResponse(
            intent="QUERY_AVAILABLE_SEATS",
            result_type="AVAILABLE_SEAT_LIST",
            result=result.model_dump(),
        )

    def _query_seat_attributes(
        self,
        current_student: StudentContext,
        parsed_intent: IntentParseResult,
    ) -> AssistantQueryResponse:
        requested_attribute = parsed_intent.seat_attribute or "WINDOW"
        items: list[AssistantSeatAttributeItem] = []
        filters = self._build_attribute_filters(requested_attribute)
        for room in self._list_visible_rooms(current_student):
            seat_payload = self.seat_service.list_student_seats(current_student, room.room_id, filters)
            for seat in seat_payload["items"]:
                items.append(
                    AssistantSeatAttributeItem(
                        seat_id=seat["seat_id"],
                        seat_code=seat["seat_code"],
                        seat_label=seat["seat_label"],
                        room_id=room.room_id,
                        room_name=room.room_name,
                        is_window_side=seat["is_window_side"],
                        has_power_socket=seat["has_power_socket"],
                        has_track_socket=seat["has_track_socket"],
                    ),
                )
        result = AssistantSeatAttributeQueryResult(
            requested_attribute=requested_attribute,
            items=items,
        )
        return AssistantQueryResponse(
            intent="QUERY_WINDOW_SEATS",
            result_type="SEAT_ATTRIBUTE_LIST",
            result=result.model_dump(),
        )

    def _query_today_my_reservation(self, current_student: StudentContext) -> AssistantQueryResponse:
        today = dt_date.today()
        visible_room_names = {
            room.room_id: room.room_name
            for room in self._list_visible_rooms(current_student)
        }
        items = [
            AssistantTodayReservationItem(
                reservation_id=reservation["reservation_id"],
                status=reservation["status"],
                seat_id=reservation["seat_id"],
                room_id=reservation["room_id"],
                room_name=visible_room_names.get(reservation["room_id"]),
                start_time=reservation["start_time"],
                end_time=reservation["end_time"],
            )
            for reservation in self._list_today_reservations(current_student, today)
        ]
        result = AssistantTodayMyReservationResult(query_date=today, items=items)
        return AssistantQueryResponse(
            intent="QUERY_TODAY_MY_RESERVATION",
            result_type="TODAY_MY_RESERVATION",
            result=result.model_dump(),
        )

    def _build_controlled_failure(
        self,
        *,
        intent: str | None,
        code: str,
        message: str,
    ) -> AssistantQueryResponse:
        result = AssistantControlledFailureResult(code=code, message=message)
        return AssistantQueryResponse(
            intent=intent,
            result_type="CONTROLLED_FAILURE",
            result=result.model_dump(),
        )

    def _list_visible_rooms(self, current_student: StudentContext) -> list[VisibleRoomSnapshot]:
        rooms: list[VisibleRoomSnapshot] = []
        page = 1
        while True:
            payload = self.room_service.list_student_rooms(
                current_student,
                page=page,
                page_size=_ROOM_PAGE_SIZE,
            )
            rooms.extend(
                VisibleRoomSnapshot(
                    room_id=item["id"],
                    room_name=item["name"],
                    open_time=item["open_time"],
                    close_time=item["close_time"],
                )
                for item in payload["items"]
            )
            if page * _ROOM_PAGE_SIZE >= payload["total"]:
                return rooms
            page += 1

    def _list_today_reservations(
        self,
        current_student: StudentContext,
        today: dt_date,
    ) -> list[dict[str, object]]:
        reservations: list[dict[str, object]] = []
        page = 1
        while True:
            payload = self.history_service.list_student_history(
                current_student,
                page=page,
                page_size=_RESERVATION_PAGE_SIZE,
            )
            reservations.extend(
                item
                for item in payload["items"]
                if item["start_time"].date() == today
            )
            if page * _RESERVATION_PAGE_SIZE >= payload["total"]:
                return reservations
            page += 1

    def _build_attribute_filters(self, requested_attribute: AssistantSeatAttribute) -> SeatFilterParams:
        if requested_attribute == "WINDOW":
            return SeatFilterParams(is_window_side=True)
        if requested_attribute == "TRACK_SOCKET":
            return SeatFilterParams(has_track_socket=True)
        return SeatFilterParams(has_power_socket=True)

    def _resolve_tonight_window(
        self,
        query_date: dt_date,
        open_time: dt_time,
        close_time: dt_time,
    ) -> tuple[datetime, datetime] | None:
        start_time = max(open_time, _EVENING_START_TIME)
        if start_time >= close_time:
            return None
        return (
            datetime.combine(query_date, start_time),
            datetime.combine(query_date, close_time),
        )

    def _format_time_range(self, start_time: dt_time, end_time: dt_time) -> str:
        return f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"

    def _list_occupied_seat_ids(
        self,
        room_id: int,
        *,
        start_time: datetime,
        end_time: datetime,
    ) -> set[int]:
        return {
            snapshot.seat_id
            for snapshot in self.assistant_reservation_service.list_occupied_seat_snapshots(
                room_id,
                start_time=start_time,
                end_time=end_time,
            )
        }
