from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.violation.models.user_reservation_block import UserReservationBlock


class ManualBlockRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_block_for_user(self, user_id: int) -> UserReservationBlock | None:
        statement = select(UserReservationBlock).where(
            UserReservationBlock.user_id == user_id,
            UserReservationBlock.released_at.is_(None),
        )
        return self.session.scalar(statement)

    def add(self, block: UserReservationBlock) -> UserReservationBlock:
        self.session.add(block)
        self.session.flush()
        return block

    def release(
        self,
        block: UserReservationBlock,
        *,
        admin_user_id: int,
        released_at: datetime,
    ) -> UserReservationBlock:
        block.released_by_admin_id = admin_user_id
        block.released_at = released_at
        self.session.add(block)
        self.session.flush()
        return block
