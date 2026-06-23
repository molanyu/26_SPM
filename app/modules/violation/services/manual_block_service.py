from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.modules.identity.constants import VIOLATION_MANUAL_BLOCKS_WRITE
from app.modules.identity.models.user import User
from app.modules.identity.services.permission_service import PermissionService
from app.modules.violation.models.user_reservation_block import UserReservationBlock
from app.modules.violation.repositories.manual_block_repository import ManualBlockRepository
from app.modules.violation.schemas.violation import ManualBlockActionRead


class ManualBlockService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ManualBlockRepository(session)
        self.permission_service = PermissionService(session)

    def activate_manual_reservation_block(
        self,
        *,
        user_id: int,
        reason: str,
        admin_user_id: int,
    ) -> UserReservationBlock:
        self._ensure_write_permission(admin_user_id)
        self._ensure_user_exists(user_id)
        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise BadRequestError("手动限制原因不能为空。")

        existing = self.repository.get_active_block_for_user(user_id)
        if existing is not None:
            return existing

        block = UserReservationBlock(
            user_id=user_id,
            reason=cleaned_reason,
            created_by_admin_id=admin_user_id,
            created_at=datetime.now(),
            released_by_admin_id=None,
            released_at=None,
        )
        try:
            with self.session.begin_nested():
                created = self.repository.add(block)
        except IntegrityError:
            existing = self.repository.get_active_block_for_user(user_id)
            if existing is None:
                raise
            return existing
        self.session.commit()
        return created

    def release_manual_reservation_block(
        self,
        *,
        user_id: int,
        admin_user_id: int,
    ) -> UserReservationBlock:
        self._ensure_write_permission(admin_user_id)
        self._ensure_user_exists(user_id)
        block = self.repository.get_active_block_for_user(user_id)
        if block is None:
            raise BadRequestError("该用户当前不存在有效的手动预约限制。")
        released = self.repository.release(block, admin_user_id=admin_user_id, released_at=datetime.now())
        self.session.commit()
        return released

    def build_action_read(
        self,
        *,
        user_id: int,
        manual_block_id: int,
        released_at: datetime | None = None,
    ) -> ManualBlockActionRead:
        from app.modules.violation.services.violation_service import ViolationService

        status = ViolationService(self.session).get_user_penalty_status(user_id)
        return ManualBlockActionRead(
            user_id=user_id,
            manual_block_id=manual_block_id,
            is_penalized=status.is_penalized,
            restriction_source=status.restriction_source,
            manual_block_reason=status.manual_block_reason,
            manual_block_started_at=status.manual_block_started_at,
            released_at=released_at,
        )

    def _ensure_write_permission(self, admin_user_id: int) -> None:
        self.permission_service.ensure_permission(admin_user_id, VIOLATION_MANUAL_BLOCKS_WRITE)

    def _ensure_user_exists(self, user_id: int) -> None:
        if self.session.get(User, user_id) is None:
            raise NotFoundError("目标用户不存在。")
