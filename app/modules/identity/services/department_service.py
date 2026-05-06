from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.identity.models.department import Department
from app.modules.identity.repositories.department_repository import DepartmentRepository
from app.modules.identity.schemas.department import DepartmentCreateRequest


class DepartmentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.department_repository = DepartmentRepository(session)

    def list_active_departments(self) -> list[Department]:
        return self.department_repository.list_active()

    def list_departments(self) -> list[Department]:
        return self.department_repository.list_all()

    def get_active_department(self, department_id: int) -> Department | None:
        return self.department_repository.get_active_by_id(department_id)

    def create_department(self, payload: DepartmentCreateRequest) -> Department:
        self._ensure_department_unique(name=payload.name, code=payload.code)
        department = Department(
            name=payload.name,
            code=payload.code,
            is_active=payload.is_active,
        )
        try:
            return self.department_repository.create(department)
        except IntegrityError as exc:
            self.session.rollback()
            raise self._map_integrity_error(payload, exc) from exc

    def activate_department(self, department_id: int) -> Department:
        department = self._get_department_or_404(department_id)
        department.is_active = True
        return self.department_repository.save(department)

    def deactivate_department(self, department_id: int) -> Department:
        department = self._get_department_or_404(department_id)
        department.is_active = False
        return self.department_repository.save(department)

    def _get_department_or_404(self, department_id: int) -> Department:
        department = self.department_repository.get_by_id(department_id)
        if department is None:
            raise NotFoundError("未找到该院系。")
        return department

    def _ensure_department_unique(self, *, name: str, code: str) -> None:
        if self.department_repository.get_by_name(name) is not None:
            raise ConflictError(
                "院系名称已存在，请更换后重试。",
                details={"field": "name", "value": name},
            )
        if self.department_repository.get_by_code(code) is not None:
            raise ConflictError(
                "院系编码已存在，请更换后重试。",
                details={"field": "code", "value": code},
            )

    def _map_integrity_error(
        self,
        payload: DepartmentCreateRequest,
        exc: IntegrityError,
    ) -> ConflictError:
        detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
        if "name" in detail:
            return ConflictError(
                "院系名称已存在，请更换后重试。",
                details={"field": "name", "value": payload.name},
            )
        if "code" in detail:
            return ConflictError(
                "院系编码已存在，请更换后重试。",
                details={"field": "code", "value": payload.code},
            )
        return ConflictError("院系已存在，请检查名称和编码后重试。")
