from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NotificationType = Literal["RESERVATION_REMINDER", "NO_SHOW_REMINDER", "AUTO_CANCEL_NOTICE"]
NotificationChannel = Literal["MOCK"]


class NotificationRequest(BaseModel):
    notification_type: NotificationType
    reservation_id: int
    user_id: int
    message: str
    channel: NotificationChannel = "MOCK"


class NotificationReservationSnapshot(BaseModel):
    reservation_id: int
    user_id: int
    room_id: int
    seat_id: int
    start_time: datetime
    end_time: datetime
    status: str
