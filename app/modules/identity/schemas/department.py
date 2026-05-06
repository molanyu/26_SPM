from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class DepartmentCreateRequest(BaseModel):
    name: str
    code: str
    is_active: bool = True

    @model_validator(mode="after")
    def normalize_department(self) -> Self:
        self.name = self.name.strip()
        self.code = self.code.strip()
        if not self.name:
            raise ValueError("院系名称不能为空。")
        if not self.code:
            raise ValueError("院系编码不能为空。")
        return self


class DepartmentRead(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
