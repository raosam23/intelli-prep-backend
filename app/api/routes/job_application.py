import uuid
from app.services.job_application_service import (
    create_job_application,
    get_job_applications,
    get_job_application_by_id,
    update_job_application,
    delete_job_application
)
from app.schemas.job_application import (
    CreateJobApplicationRequest,
    UpdateJobApplicationRequest,
    JobApplicationResponse,
    JobApplicationListResponse
)
from app.models.user import User
from app.db.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user
from typing import Dict

router = APIRouter()

@router.post("/", response_model=JobApplicationResponse)
async def create_application(data: CreateJobApplicationRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> JobApplicationResponse:
    return await create_job_application(session, current_user.id, data)

@router.get("/", response_model=JobApplicationListResponse)
async def list_applications(session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> JobApplicationListResponse:
    return await get_job_applications(session, current_user.id)

@router.get("/{application_id}", response_model=JobApplicationResponse)
async def get_application(application_id: uuid.UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> JobApplicationResponse:
    return await get_job_application_by_id(session, current_user.id, application_id)

@router.put("/{application_id}", response_model=JobApplicationResponse)
async def update_application(application_id: uuid.UUID, data: UpdateJobApplicationRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> JobApplicationResponse:
    return await update_job_application(session, current_user.id, application_id, data)

@router.delete("/{application_id}", response_model=Dict[str, str])
async def delete_application(application_id: uuid.UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    return await delete_job_application(session, current_user.id, application_id)
