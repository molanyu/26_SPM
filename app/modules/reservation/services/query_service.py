from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.reservation.repositories.reservation_repository import ReservationRepository
from app.modules.reservation.schemas.reservation import AdminReservationQueryFilters, ReservationWriteData
from app.modules.reservation.services.reservation_service import build_reservation_write_data


@dataclass(slots=True)
class ReservationRecordListResult:
    items: list[ReservationWriteData]
    total: int
    page: int
    page_size: int


class ReservationQueryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ReservationRepository(session)

    def list_admin_records(self, filters: AdminReservationQueryFilters) -> ReservationRecordListResult:
        reservations = self.repository.list_admin_records(filters)
        total = self.repository.count_admin_records(filters)
        items = [build_reservation_write_data(reservation) for reservation in reservations]
        return ReservationRecordListResult(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )
