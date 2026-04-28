from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.identity.dependencies import get_auth_service, get_current_student
from app.modules.identity.models.user import User
from app.modules.identity.schemas.auth import StudentLoginRequest, StudentLoginResponse
from app.modules.identity.schemas.user import DepartmentRead, StudentMeResponse
from app.modules.identity.services.auth_service import AuthService

router = APIRouter(prefix="/student", tags=["identity-student"])


def _build_student_me(user: User) -> StudentMeResponse:
    department = DepartmentRead.model_validate(user.department) if user.department else None
    return StudentMeResponse(
        id=user.id,
        name=user.name,
        student_no=user.student_no,
        department=department,
    )


@router.post("/auth/login", response_model=StudentLoginResponse)
def login_student(
    payload: StudentLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> StudentLoginResponse:
    token, user = auth_service.login_student(payload.student_no, payload.password)
    return StudentLoginResponse(access_token=token, token_type="bearer", user=_build_student_me(user))


@router.get("/me", response_model=StudentMeResponse)
def get_student_me(current_student: User = Depends(get_current_student)) -> StudentMeResponse:
    return _build_student_me(current_student)

