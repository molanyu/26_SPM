from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.routes.dependencies import require_admin_portal_permission
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService
from app.core.database import get_db
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ
from app.modules.identity.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-portal-statistics"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


@router.get("/statistics")
def statistics_page(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(IDENTITY_PERMISSIONS_READ)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    try:
        context = page_service.get_statistics_context(
            request,
            current_admin,
            date_from=date_from,
            date_to=date_to,
        )
        return render_page("statistics", context)
    except ValidationError as exc:
        resolved_date_from = date_from or date.today()
        resolved_date_to = date_to or resolved_date_from
        context = page_service.build_base_context(
            request,
            current_admin,
            page_title="统计查询",
            page_key="statistics.usage",
            page_intro="查看使用率与违约率统计结果，页面查询条件与既有统计接口保持一致。",
            error_message=page_service.format_exception_message(exc),
            overview={
                "total_reserved_minutes": 0,
                "total_violation_count": 0,
                "overall_violation_rate": 0.0,
            },
            rooms=[],
            seats=[],
            filters={
                "date_from": resolved_date_from,
                "date_to": resolved_date_to,
            },
        )
        return render_page("statistics", context, status_code=page_service.html_error_status(exc))
