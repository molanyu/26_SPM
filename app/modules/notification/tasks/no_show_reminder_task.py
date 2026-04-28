from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.notification.services.reminder_service import ReminderService


def send_no_show_reminders(session: Session, *, now: datetime | None = None):
    return ReminderService(session).send_no_show_reminders(now=now)
