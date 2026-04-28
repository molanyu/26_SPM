from __future__ import annotations

from datetime import time
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

DepartmentScope = Literal["PUBLIC", "DEPARTMENT"]


class StudentRoomRead(BaseModel):
    id: int
    name: str
    location: str
    open_time: time
    close_time: time
    department_scope: DepartmentScope


class AdminRoomRead(BaseModel):
    id: int
    name: str
    location: str
    department_id: int | None = None
    is_department_only: bool
    is_active: bool
    open_time: time
    close_time: time

    model_config = ConfigDict(from_attributes=True)


class RoomCreateRequest(BaseModel):
    name: str
    location: str
    department_id: int | None = None
    is_department_only: bool = False
    is_active: bool = True
    open_time: time
    close_time: time

    @model_validator(mode="after")
    def validate_resource_room(self) -> Self:
        if self.is_department_only and self.department_id is None:
            raise ValueError("院系专属自习室必须选择所属院系。")
        if self.open_time >= self.close_time:
            raise ValueError("开放时间必须早于关闭时间。")
        return self


class RoomUpdateRequest(RoomCreateRequest):
    pass
