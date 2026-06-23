from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ, VIOLATION_MANUAL_BLOCKS_WRITE
from app.modules.identity.dependencies import require_admin_permission
from app.modules.identity.models.user import User
from app.modules.violation.schemas.violation import ViolationQueryFilters
from app.modules.violation.schemas.violation import ManualBlockCreateRequest
from app.modules.violation.services.manual_block_service import ManualBlockService
from app.modules.violation.services.query_service import QueryService

router = APIRouter(
    prefix="/admin",
    tags=["violation-admin"],
)


def get_query_service(db: Session = Depends(get_db)) -> QueryService:
    return QueryService(db)


def get_manual_block_service(db: Session = Depends(get_db)) -> ManualBlockService:
    return ManualBlockService(db)


@router.get("/violations")
def list_violations(
    user_id: int | None = None,
    student_no: str | None = None,
    room_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_admin_permission(IDENTITY_PERMISSIONS_READ)),
    query_service: QueryService = Depends(get_query_service),
):
    filters = ViolationQueryFilters(
        user_id=user_id,
        student_no=student_no,
        room_id=room_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    result = query_service.list_records(filters)
    return {
        "items": [item.model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "user_summary": result.user_summary.model_dump() if result.user_summary else None,
    }


@router.post("/violations/users/{user_id}/manual-block")
def activate_manual_block(
    user_id: int,
    payload: ManualBlockCreateRequest,
    current_admin: User = Depends(require_admin_permission(VIOLATION_MANUAL_BLOCKS_WRITE)),
    manual_block_service: ManualBlockService = Depends(get_manual_block_service),
):
    block = manual_block_service.activate_manual_reservation_block(
        user_id=user_id,
        reason=payload.reason,
        admin_user_id=current_admin.id,
    )
    data = manual_block_service.build_action_read(user_id=user_id, manual_block_id=block.id)
    return {
        "success": True,
        "message": "Manual reservation block activated.",
        "data": data.model_dump(),
    }


@router.post("/violations/users/{user_id}/manual-block/release")
def release_manual_block(
    user_id: int,
    current_admin: User = Depends(require_admin_permission(VIOLATION_MANUAL_BLOCKS_WRITE)),
    manual_block_service: ManualBlockService = Depends(get_manual_block_service),
):
    block = manual_block_service.release_manual_reservation_block(
        user_id=user_id,
        admin_user_id=current_admin.id,
    )
    data = manual_block_service.build_action_read(
        user_id=user_id,
        manual_block_id=block.id,
        released_at=block.released_at,
    )
    return {
        "success": True,
        "message": "Manual reservation block released.",
        "data": data.model_dump(),
    }
