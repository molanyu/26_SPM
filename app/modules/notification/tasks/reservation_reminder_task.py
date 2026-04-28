from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.notification.services.reminder_service import ReminderService


def send_reservation_reminders(session: Session, *, now: datetime | None = None):
    return ReminderService(session).send_reservation_reminders(now=now)
