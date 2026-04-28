from fastapi import APIRouter

from app.modules.assistant.api.student_assistant import router as student_assistant_router

router = APIRouter()
router.include_router(student_assistant_router)

