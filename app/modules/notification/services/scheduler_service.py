from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.core.database import SessionLocal
from app.modules.checkin.tasks.timeout_release_task import release_expired_reservations
from app.modules.notification.tasks.auto_cancel_notice_task import send_auto_cancel_notifications
from app.modules.notification.tasks.no_show_reminder_task import send_no_show_reminders
from app.modules.notification.tasks.reservation_reminder_task import send_reservation_reminders

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]

TASK_RESERVATION_REMINDERS = "reservation_reminders"
TASK_NO_SHOW_REMINDERS = "no_show_reminders"
TASK_EXPIRED_RELEASE = "expired_release"
TASK_AUTO_CANCEL_NOTIFICATIONS = "auto_cancel_notifications"


@dataclass(slots=True)
class SchedulerTaskOutcome:
    task_name: str
    success: bool
    reservation_ids: list[int]
    error: str | None = None


@dataclass(slots=True)
class SchedulerRunResult:
    run_at: datetime
    outcomes: list[SchedulerTaskOutcome]

    def get_ids(self, task_name: str) -> list[int]:
        for outcome in self.outcomes:
            if outcome.task_name == task_name:
                return outcome.reservation_ids
        return []

    @property
    def reservation_reminder_ids(self) -> list[int]:
        return self.get_ids(TASK_RESERVATION_REMINDERS)

    @property
    def no_show_reminder_ids(self) -> list[int]:
        return self.get_ids(TASK_NO_SHOW_REMINDERS)

    @property
    def expired_reservation_ids(self) -> list[int]:
        return self.get_ids(TASK_EXPIRED_RELEASE)

    @property
    def timeout_release_notification_ids(self) -> list[int]:
        return self.get_ids(TASK_AUTO_CANCEL_NOTIFICATIONS)

    @property
    def auto_cancel_notification_ids(self) -> list[int]:
        return self.timeout_release_notification_ids


def run_once(
    *,
    now: datetime | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> SchedulerRunResult:
    run_at = _normalize_now(now)
    outcomes: list[SchedulerTaskOutcome] = []
    with session_factory() as session:
        for task_name, task, result_attr in _ordered_tasks():
            outcomes.append(_run_task(session, task_name, task, result_attr, run_at))
    return SchedulerRunResult(run_at=run_at, outcomes=outcomes)


def tick(
    *,
    now: datetime | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> SchedulerRunResult:
    return run_once(now=now, session_factory=session_factory)


async def run_scheduler_loop(
    *,
    settings: Settings | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> None:
    resolved_settings = settings or load_settings()
    interval_seconds = max(1, resolved_settings.task_scheduler_interval_seconds)
    while True:
        try:
            run_once(session_factory=session_factory)
        except Exception:
            logger.exception("Notification task scheduler loop failed unexpectedly.")
        await asyncio.sleep(interval_seconds)


def _run_task(
    session: Session,
    task_name: str,
    task: Callable[..., Any],
    result_attr: str,
    run_at: datetime,
) -> SchedulerTaskOutcome:
    try:
        result = task(session, now=run_at)
        ids = list(getattr(result, result_attr, []))
        return SchedulerTaskOutcome(task_name=task_name, success=True, reservation_ids=ids)
    except Exception as exc:
        session.rollback()
        logger.exception("Scheduled task failed: %s", task_name)
        return SchedulerTaskOutcome(
            task_name=task_name,
            success=False,
            reservation_ids=[],
            error=str(exc),
        )


def _ordered_tasks() -> tuple[tuple[str, Callable[..., Any], str], ...]:
    return (
        (TASK_RESERVATION_REMINDERS, send_reservation_reminders, "sent_reservation_ids"),
        (TASK_NO_SHOW_REMINDERS, send_no_show_reminders, "sent_reservation_ids"),
        (TASK_EXPIRED_RELEASE, release_expired_reservations, "expired_reservation_ids"),
        (TASK_AUTO_CANCEL_NOTIFICATIONS, send_auto_cancel_notifications, "sent_reservation_ids"),
    )


def _normalize_now(now: datetime | None) -> datetime:
    current = now or datetime.now()
    return current.replace(second=0, microsecond=0)
