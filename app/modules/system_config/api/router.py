from fastapi import APIRouter

from app.modules.system_config.api.admin_system_config import router as admin_system_config_router

router = APIRouter()
router.include_router(admin_system_config_router)
