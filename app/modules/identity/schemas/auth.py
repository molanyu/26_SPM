from __future__ import annotations

from pydantic import BaseModel

from app.modules.identity.schemas.user import AdminMeResponse, StudentMeResponse


class StudentLoginRequest(BaseModel):
    student_no: str
    password: str


class StudentLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: StudentMeResponse


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginData(BaseModel):
    user: AdminMeResponse
