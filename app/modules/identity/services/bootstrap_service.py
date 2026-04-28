from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.modules.identity.constants import (
    BASE_PERMISSION_DEFINITIONS,
    SYSTEM_ADMIN_ROLE_CODE,
    SYSTEM_ADMIN_ROLE_NAME,
)
from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.models.role_permission import RolePermission
from app.modules.identity.models.user import User
from app.modules.identity.models.user_role import UserRole


class BootstrapService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def bootstrap(self, *, admin_email: str, admin_name: str, admin_password: str) -> None:
        permissions = self._ensure_base_permissions()
        admin_role = self._ensure_system_admin_role(permissions)
        self._ensure_first_admin(
            admin_email=admin_email.strip(),
            admin_name=admin_name.strip() or SYSTEM_ADMIN_ROLE_NAME,
            admin_password=admin_password,
            admin_role=admin_role,
        )
        self.session.commit()

    def _ensure_base_permissions(self) -> list[Permission]:
        existing = {
            permission.code: permission
            for permission in self.session.scalars(select(Permission).order_by(Permission.id))
        }
        for definition in BASE_PERMISSION_DEFINITIONS:
            if definition["code"] not in existing:
                permission = Permission(
                    name=definition["name"],
                    code=definition["code"],
                    description=definition["description"],
                )
                self.session.add(permission)
                self.session.flush()
                existing[permission.code] = permission
        return [existing[definition["code"]] for definition in BASE_PERMISSION_DEFINITIONS]

    def _ensure_system_admin_role(self, permissions: list[Permission]) -> Role:
        stmt = (
            select(Role)
            .where(Role.code == SYSTEM_ADMIN_ROLE_CODE)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        )
        role = self.session.scalar(stmt)
        if role is None:
            role = Role(
                name=SYSTEM_ADMIN_ROLE_NAME,
                code=SYSTEM_ADMIN_ROLE_CODE,
                description="Bootstrap system administrator role.",
                is_active=True,
            )
            role.role_permissions = [RolePermission(permission=permission) for permission in permissions]
            self.session.add(role)
            self.session.flush()
            return role

        return role

    def _ensure_first_admin(
        self,
        *,
        admin_email: str,
        admin_name: str,
        admin_password: str,
        admin_role: Role,
    ) -> None:
        stmt = (
            select(User)
            .where(User.email == admin_email)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        admin_user = self.session.scalar(stmt)
        if admin_user is None:
            admin_user = User(
                email=admin_email,
                name=admin_name,
                password_hash=hash_password(admin_password),
                is_active=True,
            )
            self.session.add(admin_user)
            self.session.flush()
            admin_user.user_roles.append(UserRole(role=admin_role))
            self.session.add(admin_user)
            self.session.flush()
