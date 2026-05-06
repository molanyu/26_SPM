from __future__ import annotations

from fastapi import APIRouter

from app.admin_portal.routes import (
    admin_checkin,
    admin_department,
    admin_home,
    admin_identity,
    admin_login,
    admin_notification,
    admin_reservation,
    admin_resource,
    admin_statistics,
    admin_system_config,
    admin_violation,
)

router = APIRouter()
router.include_router(admin_login.router)
router.include_router(admin_home.router)
router.include_router(admin_department.router)
router.include_router(admin_identity.router)
router.include_router(admin_resource.router)
router.include_router(admin_system_config.router)
router.include_router(admin_reservation.router)
router.include_router(admin_checkin.router)
router.include_router(admin_statistics.router)
router.include_router(admin_violation.router)
router.include_router(admin_notification.router)
