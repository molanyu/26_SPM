from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.models.role_permission import RolePermission
from app.modules.identity.models.user_role import UserRole


class PermissionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.id)
        return list(self.session.scalars(stmt))

    def get_many_by_ids(self, permission_ids: list[int]) -> list[Permission]:
        if not permission_ids:
            return []
        stmt = select(Permission).where(Permission.id.in_(permission_ids)).order_by(Permission.id)
        return list(self.session.scalars(stmt))

    def list_permissions_for_user(self, user_id: int) -> list[Permission]:
        stmt = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.is_active.is_(True))
            .distinct()
            .order_by(Permission.code)
        )
        return list(self.session.scalars(stmt))

    def user_has_permission(self, user_id: int, permission_code: str) -> bool:
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                Permission.code == permission_code,
                Role.is_active.is_(True),
            )
            .limit(1)
        )
        return self.session.scalar(stmt) is not None

