from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.interview_session import InterviewSession, InterviewStatus
from app.schemas.interview_session import CreateInterviewSessionRequest, InterviewSessionResponse, InterviewSessionListResponse
from app.models.job_application import JobApplication
from app.models.user import User
from datetime import datetime, timezone
from typing import Dict
import uuid

async def create_interview_session(session: AsyncSession, current_user: User, data: CreateInterviewSessionRequest) -> InterviewSessionResponse:
    if not (job_application := await session.get(JobApplication, data.job_application_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
    if job_application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to create an interview session for this job application")
    interview_session = InterviewSession(
        job_application_id=data.job_application_id,
        num_questions=data.num_questions,
        difficulty=data.difficulty,
        interview_type=data.interview_type,
        focus_area=data.focus_area,
        status=InterviewStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(interview_session)
    await session.commit()
    await session.refresh(interview_session)
    return InterviewSessionResponse.model_validate(interview_session)

async def get_interview_sessions_by_job_application(session: AsyncSession, current_user: User, job_application_id: uuid.UUID) -> InterviewSessionListResponse:
    if not (job_application := await session.get(JobApplication, job_application_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
    if job_application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access interview sessions for this job application")
    result = await session.execute(select(InterviewSession).where(InterviewSession.job_application_id == job_application_id))
    interview_sessions = result.scalars().all()
    return InterviewSessionListResponse(
        interview_sessions=[InterviewSessionResponse.model_validate(interview_session) for interview_session in interview_sessions],
        total=len(interview_sessions)
    )

async def get_interview_session_by_id(session: AsyncSession, current_user: User, interview_session_id: uuid.UUID) -> InterviewSessionResponse:
    if not (interview_session := await session.get(InterviewSession, interview_session_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    if not (job_application := await session.get(JobApplication, interview_session.job_application_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated job application not found")
    if job_application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this interview session")
    return InterviewSessionResponse.model_validate(interview_session)

async def delete_interview_session(session: AsyncSession, current_user: User, interview_session_id: uuid.UUID) -> Dict[str, str]:
    if not (interview_session := await session.get(InterviewSession, interview_session_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    if not (job_application := await session.get(JobApplication, interview_session.job_application_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated job application not found")
    if job_application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this interview session")
    if interview_session.status != InterviewStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending interview sessions can be deleted")
    await session.delete(interview_session)
    await session.commit()
    return {"message": "Interview session deleted successfully"}
    
