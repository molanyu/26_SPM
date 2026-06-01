from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.admin_portal.routes.dependencies import require_admin_portal_permission
from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService, prefers_html
from app.core.database import get_db
from app.core.errors import BadRequestError
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-portal-notification"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


def _parse_optional_int(value: str | None, field_name: str) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise BadRequestError(f"{field_name} 必须是数字。") from exc
    if parsed < 1:
        raise BadRequestError(f"{field_name} 必须大于 0。")
    return parsed


@router.get("/notifications")
def notifications_page(
    request: Request,
    reservation_id: str | None = None,
    notification_type: str | None = None,
    status: str | None = None,
    page: str | None = "1",
    page_size: str | None = "20",
    current_admin: User | RedirectResponse = Depends(require_admin_portal_permission(ADMIN_PORTAL_ACCESS)),
    page_service: AdminPageService = Depends(get_page_service),
):
    if isinstance(current_admin, RedirectResponse):
        return current_admin
    try:
        resolved_reservation_id = _parse_optional_int(reservation_id, "预约 ID")
        resolved_page = _parse_optional_int(page, "页码") or 1
        resolved_page_size = _parse_optional_int(page_size, "每页条数") or 20
        if not prefers_html(request):
            logs = page_service.admin_notification_service.list_logs(
                reservation_id=resolved_reservation_id,
                notification_type=notification_type.strip() if notification_type else None,
                status=status.strip() if status else None,
                page=resolved_page,
                page_size=resolved_page_size,
            )
            return {
                "items": logs.items,
                "total": logs.total,
                "page": logs.page,
                "page_size": logs.page_size,
            }
        context = page_service.get_notifications_context(
            request,
            current_admin,
            reservation_id=resolved_reservation_id,
            notification_type=notification_type.strip() if notification_type else None,
            status=status.strip() if status else None,
            page=resolved_page,
            page_size=resolved_page_size,
        )
        return render_page("notifications", context)
    except BadRequestError as exc:
        if not prefers_html(request):
            raise
        context = page_service.get_notifications_context(request, current_admin, error_message=exc.message)
        return render_page("notifications", context, status_code=exc.status_code)
