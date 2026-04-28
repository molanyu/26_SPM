from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.assistant.schemas.query import AssistantQueryRequest, AssistantQueryResponse
from app.modules.assistant.services.query_service import AssistantQueryService
from app.modules.identity.dependencies import get_current_student

router = APIRouter(prefix="/student", tags=["assistant-student"])


def get_query_service(db: Session = Depends(get_db)) -> AssistantQueryService:
    return AssistantQueryService(db)


@router.post("/assistant/query")
def query_student_assistant(
    payload: AssistantQueryRequest,
    current_student: Any = Depends(get_current_student),
    query_service: AssistantQueryService = Depends(get_query_service),
) -> AssistantQueryResponse:
    return query_service.query(current_student, payload.message)

