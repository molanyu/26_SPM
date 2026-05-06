from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.models.department import Department


class DepartmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_active(self) -> list[Department]:
        statement = select(Department).where(Department.is_active.is_(True)).order_by(Department.name.asc(), Department.id.asc())
        return list(self.session.scalars(statement))

    def list_all(self) -> list[Department]:
        statement = select(Department).order_by(Department.name.asc(), Department.id.asc())
        return list(self.session.scalars(statement))

    def get_active_by_id(self, department_id: int) -> Department | None:
        statement = select(Department).where(Department.id == department_id, Department.is_active.is_(True))
        return self.session.scalar(statement)

    def get_by_id(self, department_id: int) -> Department | None:
        statement = select(Department).where(Department.id == department_id)
        return self.session.scalar(statement)

    def get_by_name(self, name: str) -> Department | None:
        statement = select(Department).where(Department.name == name)
        return self.session.scalar(statement)

    def get_by_code(self, code: str) -> Department | None:
        statement = select(Department).where(Department.code == code)
        return self.session.scalar(statement)

    def create(self, department: Department) -> Department:
        self.session.add(department)
        self.session.commit()
        self.session.refresh(department)
        return department

    def save(self, department: Department) -> Department:
        self.session.add(department)
        self.session.commit()
        self.session.refresh(department)
        return department
