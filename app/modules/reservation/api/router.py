from fastapi import APIRouter

from app.modules.reservation.api.admin_reservation import router as admin_reservation_router
from app.modules.reservation.api.student_reservation import router as student_reservation_router

router = APIRouter()
router.include_router(student_reservation_router)
router.include_router(admin_reservation_router)
