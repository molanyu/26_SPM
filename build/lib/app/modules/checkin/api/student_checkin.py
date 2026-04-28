from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.modules.checkin.schemas.checkin import (
    CheckinSuccessData,
    StudentCodeCheckinRequest,
    StudentQRCodeCheckinRequest,
)
from app.modules.checkin.services.checkin_service import CheckinService
from app.modules.identity.dependencies import get_current_student
from app.modules.identity.models.user import User

router = APIRouter(prefix="/student", tags=["checkin-student"])


def get_checkin_service(request: Request, db: Session = Depends(get_db)) -> CheckinService:
    settings: Settings = request.app.state.settings
    return CheckinService(db, settings=settings)


@router.post("/checkins/code")
def check_in_by_code(
    payload: StudentCodeCheckinRequest,
    current_student: User = Depends(get_current_student),
    checkin_service: CheckinService = Depends(get_checkin_service),
):
    result = checkin_service.check_in_by_code(current_student, payload)
    return {
        "success": True,
        "message": "Check-in completed successfully.",
        "data": CheckinSuccessData(
            checkin_record_id=result.checkin_record_id,
            reservation_id=result.reservation_id,
            status=result.status,
            room_id=result.room_id,
            seat_id=result.seat_id,
            checkin_method=result.checkin_method,
            checkin_at=result.checkin_at,
        ).model_dump(),
    }


@router.post("/checkins/qrcode")
def check_in_by_qrcode(
    payload: StudentQRCodeCheckinRequest,
    current_student: User = Depends(get_current_student),
    checkin_service: CheckinService = Depends(get_checkin_service),
):
    result = checkin_service.check_in_by_qrcode(current_student, payload)
    return {
        "success": True,
        "message": "Check-in completed successfully.",
        "data": CheckinSuccessData(
            checkin_record_id=result.checkin_record_id,
            reservation_id=result.reservation_id,
            status=result.status,
            room_id=result.room_id,
            seat_id=result.seat_id,
            checkin_method=result.checkin_method,
            checkin_at=result.checkin_at,
        ).model_dump(),
    }
