from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.interview_session_service import (
    create_interview_session,
    get_interview_sessions_by_job_application,
    get_interview_session_by_id,
    delete_interview_session
)
from app.schemas.interview_session import (
    CreateInterviewSessionRequest,
    InterviewSessionResponse,
    InterviewSessionListResponse
)
from typing import Dict
import uuid

router = APIRouter()

@router.post("/", response_model=InterviewSessionResponse)
async def create_session(data: CreateInterviewSessionRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> InterviewSessionResponse:
    return await create_interview_session(session, current_user, data)

@router.get("/job-application/{job_application_id}", response_model=InterviewSessionListResponse)
async def list_sessions_by_job_application(job_application_id: uuid.UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> InterviewSessionListResponse:
    return await get_interview_sessions_by_job_application(session, current_user, job_application_id)

@router.get("/{interview_session_id}", response_model=InterviewSessionResponse)
async def get_interview_session(interview_session_id: uuid.UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> InterviewSessionResponse:
    return await get_interview_session_by_id(session, current_user, interview_session_id)

@router.delete("/{interview_session_id}", response_model=Dict[str, str])
async def delete_session(interview_session_id: uuid.UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    return await delete_interview_session(session, current_user, interview_session_id)