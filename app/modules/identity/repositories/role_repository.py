from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.models.role_permission import RolePermission


class RoleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _with_permissions(self, stmt):
        return stmt.options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission),
        )

    def list_roles(self) -> list[Role]:
        stmt = self._with_permissions(select(Role).order_by(Role.id))
        return list(self.session.scalars(stmt))

    def get_by_id(self, role_id: int) -> Role | None:
        stmt = self._with_permissions(select(Role).where(Role.id == role_id))
        return self.session.scalar(stmt)

    def get_by_code(self, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code)
        return self.session.scalar(stmt)

    def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self.session.scalar(stmt)

    def get_many_by_ids(self, role_ids: list[int]) -> list[Role]:
        if not role_ids:
            return []
        stmt = select(Role).where(Role.id.in_(role_ids)).order_by(Role.id)
        return list(self.session.scalars(stmt))

    def create_role(
        self,
        *,
        name: str,
        code: str,
        description: str | None,
        is_active: bool,
        permissions: list[Permission],
    ) -> Role:
        role = Role(name=name, code=code, description=description, is_active=is_active)
        role.role_permissions = [RolePermission(permission=permission) for permission in permissions]
        self.session.add(role)
        self.session.commit()
        return self.get_by_id(role.id) or role

    def update_role(
        self,
        role: Role,
        *,
        name: str,
        code: str,
        description: str | None,
        is_active: bool,
        permissions: list[Permission],
    ) -> Role:
        role.name = name
        role.code = code
        role.description = description
        role.is_active = is_active
        role.role_permissions.clear()
        self.session.flush()
        role.role_permissions.extend(RolePermission(permission=permission) for permission in permissions)
        self.session.add(role)
        self.session.commit()
        return self.get_by_id(role.id) or role

    def deactivate_role(self, role: Role) -> Role:
        role.is_active = False
        self.session.add(role)
        self.session.commit()
        return self.get_by_id(role.id) or role
