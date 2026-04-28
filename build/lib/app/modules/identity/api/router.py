from __future__ import annotations

from fastapi import APIRouter

from app.modules.identity.api import admin_auth, admin_rbac, student_auth

router = APIRouter()
router.include_router(student_auth.router)
router.include_router(admin_auth.router)
router.include_router(admin_rbac.router)

