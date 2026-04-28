from __future__ import annotations

from fastapi import APIRouter

from app.admin_portal.routes import (
    admin_home,
    admin_identity,
    admin_reservation,
    admin_resource,
    admin_system_config,
    admin_violation,
)

router = APIRouter()
router.include_router(admin_home.router)
router.include_router(admin_identity.router)
router.include_router(admin_resource.router)
router.include_router(admin_system_config.router)
router.include_router(admin_reservation.router)
router.include_router(admin_violation.router)
