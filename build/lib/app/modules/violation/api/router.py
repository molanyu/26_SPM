from fastapi import APIRouter

from app.modules.violation.api.admin_statistics import router as admin_statistics_router
from app.modules.violation.api.admin_violation import router as admin_violation_router

router = APIRouter()
router.include_router(admin_statistics_router)
router.include_router(admin_violation_router)
