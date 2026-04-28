from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import BadRequestError
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ
from app.modules.identity.dependencies import require_admin_permission
from app.modules.violation.schemas.statistics import StatisticsQueryFilters
from app.modules.violation.services.statistics_service import StatisticsService

router = APIRouter(
    prefix="/admin",
    tags=["statistics-admin"],
    dependencies=[Depends(require_admin_permission(IDENTITY_PERMISSIONS_READ))],
)


def get_statistics_service(db: Session = Depends(get_db)) -> StatisticsService:
    return StatisticsService(db)


def get_statistics_filters(
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> StatisticsQueryFilters:
    try:
        return StatisticsQueryFilters(date_from=date_from, date_to=date_to)
    except ValidationError as exc:
        error_message = exc.errors()[0]["msg"] if exc.errors() else "Invalid statistics query parameters."
        raise BadRequestError(error_message) from exc


@router.get("/statistics/usage")
def get_usage_statistics(
    filters: StatisticsQueryFilters = Depends(get_statistics_filters),
    statistics_service: StatisticsService = Depends(get_statistics_service),
):
    result = statistics_service.get_usage_statistics(filters)
    return result.model_dump()
