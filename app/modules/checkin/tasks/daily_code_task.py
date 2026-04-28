from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.checkin.services.code_service import CodeService


def generate_daily_checkin_codes(
    session: Session,
    *,
    run_date: date | None = None,
    now: datetime | None = None,
    settings: Settings | None = None,
):
    service = CodeService(session, settings=settings)
    return service.ensure_daily_codes(code_date=run_date or (now or datetime.now()).date(), now=now)
