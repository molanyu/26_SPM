from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.identity.schemas.permission import PermissionRead
from app.modules.identity.schemas.role import RoleSummary

AccountType = Literal["student", "admin"]
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_optional_text(value: str | None) -> str | None:
    cleaned = value.strip() if value is not None else None
    return cleaned or None


def _looks_like_email(value: str) -> bool:
    return bool(_EMAIL_PATTERN.fullmatch(value))


class DepartmentRead(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class MenuRead(BaseModel):
    code: str
    label: str


class UserCreateRequest(BaseModel):
    account_type: AccountType
    name: str
    student_no: str | None = None
    email: str | None = None
    notification_email: str | None = None
    password: str
    department_id: int | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_identifier_rules(self) -> "UserCreateRequest":
        self.name = self.name.strip()
        self.student_no = _normalize_optional_text(self.student_no)
        self.email = _normalize_optional_text(self.email)
        self.notification_email = _normalize_optional_text(self.notification_email)

        if not self.name:
            raise ValueError("姓名不能为空。")
        if not self.password.strip():
            raise ValueError("密码不能为空。")

        identifier_count = int(self.student_no is not None) + int(self.email is not None)
        if identifier_count != 1:
            raise ValueError("单次请求只能提交一种登录标识。")

        if self.account_type == "student":
            if self.student_no is None:
                raise ValueError("创建学生账号时必须填写学号。")
            if self.email is not None:
                raise ValueError("创建学生账号时不能同时提交管理员登录标识。")
            if self.notification_email is not None and not _looks_like_email(self.notification_email):
                raise ValueError("通知邮箱格式不正确。")
        else:
            if self.email is None:
                raise ValueError("创建管理员账号时必须填写登录标识。")
            if self.student_no is not None:
                raise ValueError("创建管理员账号时不能同时提交学号。")
            if self.notification_email is not None:
                raise ValueError("创建管理员账号时不能提交学生通知邮箱。")

        return self


class UserCreateResult(BaseModel):
    id: int
    name: str
    account_type: AccountType
    student_no: str | None = None
    email: str | None = None
    notification_email: str | None = None
    department: DepartmentRead | None = None
    is_active: bool


class UserNotificationTarget(BaseModel):
    id: int
    name: str
    email: str | None = None
    is_active: bool


class StudentMeResponse(BaseModel):
    id: int
    name: str
    student_no: str | None = None
    department: DepartmentRead | None = None


class AdminMeResponse(BaseModel):
    id: int
    name: str
    email: str | None = None
    roles: list[RoleSummary] = Field(default_factory=list)
    permissions: list[PermissionRead] = Field(default_factory=list)
    menus: list[MenuRead] = Field(default_factory=list)
