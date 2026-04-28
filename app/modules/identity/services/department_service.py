from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.identity.models.department import Department
from app.modules.identity.repositories.department_repository import DepartmentRepository


class DepartmentService:
    def __init__(self, session: Session) -> None:
        self.department_repository = DepartmentRepository(session)

    def list_active_departments(self) -> list[Department]:
        return self.department_repository.list_active()

    def get_active_department(self, department_id: int) -> Department | None:
        return self.department_repository.get_active_by_id(department_id)
