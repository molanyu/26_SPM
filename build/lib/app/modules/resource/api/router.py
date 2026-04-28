from fastapi import APIRouter

from app.modules.resource.api.admin_resource import router as admin_resource_router
from app.modules.resource.api.student_resource import router as student_resource_router

router = APIRouter()
router.include_router(student_resource_router)
router.include_router(admin_resource_router)
