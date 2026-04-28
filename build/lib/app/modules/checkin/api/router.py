from fastapi import APIRouter

from app.modules.checkin.api.student_checkin import router as student_checkin_router

router = APIRouter()
router.include_router(student_checkin_router)
