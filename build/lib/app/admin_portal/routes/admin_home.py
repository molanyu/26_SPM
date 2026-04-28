from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.page_service import AdminPageService
from app.core.database import get_db
from app.modules.identity.constants import ADMIN_PORTAL_ACCESS
from app.modules.identity.dependencies import get_current_admin, require_admin_permission
from app.modules.identity.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-portal-home"])


def get_page_service(db: Session = Depends(get_db)) -> AdminPageService:
    return AdminPageService(db)


@router.get(
    "",
    dependencies=[Depends(require_admin_permission(ADMIN_PORTAL_ACCESS))],
)
def admin_home(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    page_service: AdminPageService = Depends(get_page_service),
):
    context = page_service.get_home_context(request, current_admin)
    return render_page("home", context)
