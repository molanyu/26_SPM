from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, ConflictError
from app.core.security import hash_password
from app.modules.identity.models.department import Department
from app.modules.identity.models.user import User
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.schemas.user import (
    AccountType,
    UserCreateRequest,
    UserCreateResult,
    UserNotificationTarget,
)
from app.modules.identity.services.department_service import DepartmentService


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.department_service = DepartmentService(session)

    def create_user(self, payload: UserCreateRequest) -> UserCreateResult:
        department = self._resolve_department(payload.department_id)
        self._ensure_identifier_available(payload)

        user = User(
            student_no=payload.student_no if payload.account_type == "student" else None,
            email=payload.email if payload.account_type == "admin" else payload.notification_email,
            name=payload.name,
            password_hash=hash_password(payload.password),
            department_id=department.id if department is not None else None,
            is_active=payload.is_active,
        )

        try:
            created_user = self.user_repository.create_user(user)
        except IntegrityError as exc:
            self.session.rollback()
            raise self._map_integrity_error(payload, exc) from exc

        return self._build_user_result(created_user, payload.account_type, department)

    def get_notification_target(self, user_id: int) -> UserNotificationTarget | None:
        user = self.user_repository.get_by_id(user_id, include_inactive=True)
        if user is None:
            return None
        return UserNotificationTarget(
            id=user.id,
            name=user.name,
            email=user.email.strip() if user.email is not None else None,
            is_active=user.is_active,
        )

    def _resolve_department(self, department_id: int | None) -> Department | None:
        if department_id is None:
            return None
        department = self.department_service.get_active_department(department_id)
        if department is None:
            raise BadRequestError(
                "所选院系不存在或已停用，请重新选择。",
                details={"field": "department_id", "value": department_id},
            )
        return department

    def _ensure_identifier_available(self, payload: UserCreateRequest) -> None:
        if payload.student_no is not None:
            existing_student = self.user_repository.get_by_student_no(
                payload.student_no,
                include_inactive=True,
            )
            if existing_student is not None:
                raise ConflictError(
                    "该学号已被使用，请确认后重试。",
                    details={"field": "student_no", "value": payload.student_no},
                )

        if payload.email is not None:
            existing_admin = self.user_repository.get_by_email(
                payload.email,
                include_inactive=True,
            )
            if existing_admin is not None:
                raise ConflictError(
                    "该管理员登录标识已被使用，请更换后重试。",
                    details={"field": "email", "value": payload.email},
                )

        if payload.notification_email is not None:
            existing_notification_email = self.user_repository.get_by_email(
                payload.notification_email,
                include_inactive=True,
            )
            if existing_notification_email is not None:
                raise ConflictError(
                    "该通知邮箱已被使用，请更换后重试。",
                    details={"field": "notification_email", "value": payload.notification_email},
                )

    def _map_integrity_error(self, payload: UserCreateRequest, exc: IntegrityError) -> ConflictError | BadRequestError:
        detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
        if "student_no" in detail:
            return ConflictError(
                "该学号已被使用，请确认后重试。",
                details={"field": "student_no", "value": payload.student_no},
            )
        if "email" in detail:
            if payload.account_type == "student":
                return ConflictError(
                    "该通知邮箱已被使用，请更换后重试。",
                    details={"field": "notification_email", "value": payload.notification_email},
                )
            return ConflictError(
                "该管理员登录标识已被使用，请更换后重试。",
                details={"field": "email", "value": payload.email},
            )
        if "department" in detail:
            return BadRequestError(
                "所选院系不存在或已停用，请重新选择。",
                details={"field": "department_id", "value": payload.department_id},
            )
        return BadRequestError("用户创建失败，请检查输入后重试。")

    def _build_user_result(
        self,
        user: User,
        account_type: AccountType,
        department: Department | None,
    ) -> UserCreateResult:
        return UserCreateResult(
            id=user.id,
            name=user.name,
            account_type=account_type,
            student_no=user.student_no,
            email=user.email if account_type == "admin" else None,
            notification_email=user.email if account_type == "student" else None,
            department=department,
            is_active=user.is_active,
        )
