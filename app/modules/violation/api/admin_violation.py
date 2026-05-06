from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ
from app.modules.identity.dependencies import require_admin_permission
from app.modules.violation.schemas.violation import ViolationQueryFilters
from app.modules.violation.services.query_service import QueryService

router = APIRouter(
    prefix="/admin",
    tags=["violation-admin"],
    dependencies=[Depends(require_admin_permission(IDENTITY_PERMISSIONS_READ))],
)


def get_query_service(db: Session = Depends(get_db)) -> QueryService:
    return QueryService(db)


@router.get("/violations")
def list_violations(
    user_id: int | None = None,
    student_no: str | None = None,
    room_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
    }
