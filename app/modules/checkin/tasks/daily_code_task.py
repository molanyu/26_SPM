from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.checkin.services.code_service import CodeService


def get_current_dynamic_checkin_codes(
    session: Session,
    *,
    run_date: date | None = None,
    now: datetime | None = None,
    settings: Settings | None = None,
):
    service = CodeService(session, settings=settings)
    resolved_now = now or (datetime.combine(run_date, datetime.min.time()) if run_date is not None else None)
    return service.get_current_dynamic_codes(now=resolved_now)


generate_daily_checkin_codes = get_current_dynamic_checkin_codes
