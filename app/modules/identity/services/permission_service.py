from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, BadRequestError, ConflictError, NotFoundError
from app.modules.identity.constants import SYSTEM_ADMIN_ROLE_CODE
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
            raise ConflictError("角色编码已存在，请更换后重试。")
        if self.role_repository.get_by_name(payload.name):
            raise ConflictError("角色名称已存在，请更换后重试。")
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
            raise NotFoundError("未找到要编辑的角色。")
        existing_code = self.role_repository.get_by_code(payload.code)
        if existing_code and existing_code.id != role_id:
            raise ConflictError("角色编码已存在，请更换后重试。")
        existing_name = self.role_repository.get_by_name(payload.name)
        if existing_name and existing_name.id != role_id:
            raise ConflictError("角色名称已存在，请更换后重试。")
        permissions = self._resolve_permissions(payload.permission_ids)
        return self.role_repository.update_role(
            role,
            name=payload.name,
            code=payload.code,
            description=payload.description,
            is_active=payload.is_active,
            permissions=permissions,
        )

    def deactivate_role(self, role_id: int) -> Role:
        role = self.role_repository.get_by_id(role_id)
        if role is None:
            raise NotFoundError("未找到要停用的角色。")
        if not role.is_active:
            raise BadRequestError("该角色已处于停用状态，无需重复操作。")
        return self.role_repository.deactivate_role(role)

    def delete_role(self, role_id: int) -> None:
        role = self.role_repository.get_by_id(role_id)
        if role is None:
            raise NotFoundError("未找到要删除的角色。")
        if role.code == SYSTEM_ADMIN_ROLE_CODE:
            raise BadRequestError("系统保留角色不能删除。")
        if self.role_repository.has_user_assignments(role_id):
            raise BadRequestError("该角色已分配给用户，请先解除分配或停用角色。")
        self.role_repository.delete_role(role)

    def list_permissions(self) -> list[Permission]:
        return self.permission_repository.list_permissions()

    def assign_roles(self, user_id: int, role_ids: list[int]) -> User:
        user = self.user_repository.get_by_id(user_id, load_relationships=True, include_inactive=True)
        if user is None:
            raise NotFoundError("未找到要分配角色的用户。")
        roles = self.role_repository.get_many_by_ids(sorted(set(role_ids)))
        if len(roles) != len(set(role_ids)):
            raise BadRequestError("提交的角色中包含无效项，请刷新后重新选择。")
        if any(not role.is_active for role in roles):
            raise BadRequestError("停用的角色不能再分配给用户，请调整选择后重试。")
        return self.user_repository.replace_roles(user, roles)

    def find_user_for_role_assignment(self, user_id: int) -> User | None:
        return self.user_repository.get_by_id(
            user_id,
            load_relationships=True,
            include_inactive=True,
        )

    def resolve_user_for_role_assignment(self, identifier: str) -> User:
        cleaned = identifier.strip()
        if not cleaned:
            raise BadRequestError("请先输入要分配角色的用户 ID、邮箱或学号。")

        if ":" in cleaned:
            prefix, raw_value = cleaned.split(":", 1)
            value = raw_value.strip()
            if not value:
                raise BadRequestError("已识别到定位前缀，但没有填写实际标识。")
            return self._resolve_user_with_prefix(prefix.strip().lower(), value)

        if "@" in cleaned:
            user = self._find_user_by_email(cleaned)
            if user is not None:
                return user

        if cleaned.isdigit():
            user_by_id = self._find_user_by_id(cleaned)
            user_by_student_no = self._find_user_by_student_no(cleaned)
            if user_by_id is not None and user_by_student_no is not None and user_by_id.id != user_by_student_no.id:
                raise BadRequestError(
                    "该数字同时匹配到了用户 ID 和学号，请改用邮箱，或使用 id:/student: 前缀重新输入。"
                )
            if user_by_id is not None:
                return user_by_id
            if user_by_student_no is not None:
                return user_by_student_no

        user = self._find_user_by_student_no(cleaned)
        if user is not None:
            return user

        raise NotFoundError("未找到匹配的用户，请检查用户 ID、邮箱或学号后重试。")

    def get_user_permissions(self, user_id: int) -> list[Permission]:
        return self.permission_repository.list_permissions_for_user(user_id)

    def ensure_permission(self, user_id: int, permission_code: str) -> None:
        if not self.permission_repository.user_has_permission(user_id, permission_code):
            raise AuthorizationError("当前账号没有执行此操作所需的权限。")

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
            raise AuthorizationError("当前账号无权访问该院系专属自习室。")

    def _resolve_permissions(self, permission_ids: list[int]) -> list[Permission]:
        permissions = self.permission_repository.get_many_by_ids(sorted(set(permission_ids)))
        if len(permissions) != len(set(permission_ids)):
            raise BadRequestError("提交的权限中包含无效项，请刷新后重新选择。")
        return permissions

    def _resolve_user_with_prefix(self, prefix: str, value: str) -> User:
        if prefix in {"id", "user", "user_id"}:
            if not value.isdigit():
                raise BadRequestError("使用 id: 前缀时，后面必须填写数字用户 ID。")
            user = self._find_user_by_id(value)
        elif prefix in {"student", "student_no", "sno"}:
            user = self._find_user_by_student_no(value)
        elif prefix in {"email", "mail"}:
            user = self._find_user_by_email(value)
        else:
            raise BadRequestError("无法识别该定位方式，请使用邮箱、学号，或使用 id:/student:/email: 前缀。")
        if user is None:
            raise NotFoundError("未找到匹配的用户，请检查定位前缀和标识后重试。")
        return user

    def _find_user_by_id(self, value: str) -> User | None:
        return self.user_repository.get_by_id(
            int(value),
            load_relationships=True,
            include_inactive=True,
        )

    def _find_user_by_student_no(self, value: str) -> User | None:
        return self.user_repository.get_by_student_no(
            value,
            load_relationships=True,
            include_inactive=True,
        )

    def _find_user_by_email(self, value: str) -> User | None:
        return self.user_repository.get_by_email(
            value,
            load_relationships=True,
            include_inactive=True,
        )
