from __future__ import annotations

from dataclasses import dataclass

from app.modules.assistant.schemas.query import AssistantIntent, AssistantSeatAttribute


@dataclass(slots=True)
class IntentParseResult:
    intent: AssistantIntent | None
    seat_attribute: AssistantSeatAttribute | None = None


class IntentService:
    _TODAY_KEYWORDS = ("今天", "今日")
    _EVENING_KEYWORDS = ("今天晚上", "今晚", "晚上")
    _AVAILABLE_KEYWORDS = ("空座", "空位", "空闲座位", "空闲位置", "还有座位", "有空位", "有位置")
    _WINDOW_KEYWORDS = ("靠窗", "窗边", "窗旁")
    _TRACK_SOCKET_KEYWORDS = ("移动导轨插座", "导轨插座", "轨道插座", "导轨")
    _POWER_SOCKET_KEYWORDS = ("固定插座", "电源插座", "有插座", "插座", "电源")
    _RESERVATION_KEYWORDS = ("预约", "定了", "订了", "预定")

    def parse_message(self, message: str) -> IntentParseResult:
        normalized = self._normalize_message(message)

        if self._is_today_my_reservation_query(normalized):
            return IntentParseResult(intent="QUERY_TODAY_MY_RESERVATION")

        seat_attribute = self._extract_seat_attribute(normalized)
        if seat_attribute is not None:
            return IntentParseResult(intent="QUERY_WINDOW_SEATS", seat_attribute=seat_attribute)

        if self._is_available_seat_query(normalized):
            return IntentParseResult(intent="QUERY_AVAILABLE_SEATS")

        return IntentParseResult(intent=None)

    def _normalize_message(self, message: str) -> str:
        return (
            message.strip()
            .replace(" ", "")
            .replace("\n", "")
            .replace("\r", "")
            .replace("？", "?")
            .replace("。", "")
            .replace("，", "")
        )

    def _is_today_my_reservation_query(self, message: str) -> bool:
        return (
            "我" in message
            and any(keyword in message for keyword in self._TODAY_KEYWORDS)
            and any(keyword in message for keyword in self._RESERVATION_KEYWORDS)
        )

    def _is_available_seat_query(self, message: str) -> bool:
        return (
            any(keyword in message for keyword in self._EVENING_KEYWORDS)
            and any(keyword in message for keyword in self._AVAILABLE_KEYWORDS)
        )

    def _extract_seat_attribute(self, message: str) -> AssistantSeatAttribute | None:
        if any(keyword in message for keyword in self._WINDOW_KEYWORDS):
            return "WINDOW"
        if any(keyword in message for keyword in self._TRACK_SOCKET_KEYWORDS):
            return "TRACK_SOCKET"
        if any(keyword in message for keyword in self._POWER_SOCKET_KEYWORDS):
            return "POWER_SOCKET"
        return None

