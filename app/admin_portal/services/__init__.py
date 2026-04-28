from __future__ import annotations

from app.admin_portal.services.html_renderer import render_page
from app.admin_portal.services.menu_service import AdminPortalMenuService
from app.admin_portal.services.page_service import AdminPageService, prefers_html

__all__ = [
    "AdminPageService",
    "AdminPortalMenuService",
    "prefers_html",
    "render_page",
]
