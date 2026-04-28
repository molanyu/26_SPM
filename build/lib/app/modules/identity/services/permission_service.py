from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, BadRequestError, ConflictError, NotFoundError
from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.models.user import User
from app.modules.identity.repositories.permission_repository import PermissionRepository
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.schemas.role import RoleCreateRequest, RoleUpdateRequest


class PermissionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.permission_repository = PermissionRepository(session)
        self.role_repository = RoleRepository(session)
        self.user_repository = UserRepository(session)

    def list_roles(self) -> list[Role]:
        return self.role_repository.list_roles()

    def create_role(self, payload: RoleCreateRequest) -> Role:
        if self.role_repository.get_by_code(payload.code):
            raise ConflictError("Role code already exists.")
        if self.role_repository.get_by_name(payload.name):
            raise ConflictError("Role name already exists.")
        permissions = self._resolve_permissions(payload.permission_ids)
        return self.role_repository.create_role(
            name=payload.name,
            code=payload.code,
            description=payload.description,
            is_active=payload.is_active,
            permissions=permissions,
        )

    def update_role(self, role_id: int, payload: RoleUpdateRequest) -> Role:
        role = self.role_repository.get_by_id(role_id)
        if role is None:
            raise NotFoundError("Role does not exist.")
        existing_code = self.role_repository.get_by_code(payload.code)
        if existing_code and existing_code.id != role_id:
            raise ConflictError("Role code already exists.")
        existing_name = self.role_repository.get_by_name(payload.name)
        if existing_name and existing_name.id != role_id:
            raise ConflictError("Role name already exists.")
        permissions = self._resolve_permissions(payload.permission_ids)
        return self.role_repository.update_role(
            role,
            name=payload.name,
            code=payload.code,
            description=payload.description,
            is_active=payload.is_active,
            permissions=permissions,
        )

    def list_permissions(self) -> list[Permission]:
        return self.permission_repository.list_permissions()

    def assign_roles(self, user_id: int, role_ids: list[int]) -> User:
        user = self.user_repository.get_by_id(user_id, load_relationships=True, include_inactive=True)
        if user is None:
            raise NotFoundError("User does not exist.")
        roles = self.role_repository.get_many_by_ids(sorted(set(role_ids)))
        if len(roles) != len(set(role_ids)):
            raise BadRequestError("One or more role ids are invalid.")
        return self.user_repository.replace_roles(user, roles)

    def get_user_permissions(self, user_id: int) -> list[Permission]:
        return self.permission_repository.list_permissions_for_user(user_id)

    def ensure_permission(self, user_id: int, permission_code: str) -> None:
        if not self.permission_repository.user_has_permission(user_id, permission_code):
            raise AuthorizationError("The current user does not have the required permission.")

    def can_access_department(
        self,
        user_department_id: int | None,
        room_department_id: int | None,
        is_department_only: bool,
    ) -> bool:
        if not is_department_only:
            return True
        if room_department_id is None:
            return True
        return user_department_id == room_department_id

    def ensure_department_access(
        self,
        user_department_id: int | None,
        room_department_id: int | None,
        is_department_only: bool,
    ) -> None:
        if not self.can_access_department(user_department_id, room_department_id, is_department_only):
            raise AuthorizationError("The current user cannot access this department-scoped room.")

    def _resolve_permissions(self, permission_ids: list[int]) -> list[Permission]:
        permissions = self.permission_repository.get_many_by_ids(sorted(set(permission_ids)))
        if len(permissions) != len(set(permission_ids)):
            raise BadRequestError("One or more permission ids are invalid.")
        return permissions

