import uuid
from app.schemas.job_application import CreateJobApplicationRequest, UpdateJobApplicationRequest, JobApplicationResponse, JobApplicationListResponse
from app.models.job_application import JobApplication, ApplicationStatus
from app.models.resume import Resume
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status
from typing import Dict

async def create_job_application(session: AsyncSession, user_id: uuid.UUID, data: CreateJobApplicationRequest) -> JobApplicationResponse:
    if not (resume := await session.get(Resume, data.resume_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to use this resume")
    job_application = JobApplication(
        user_id=user_id,
        resume_id=data.resume_id,
        jd_raw_text=data.jd_raw_text,
        status=ApplicationStatus.APPLIED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(job_application)
    await session.commit()
    await session.refresh(job_application)
    return JobApplicationResponse.model_validate(job_application)

async def get_job_applications(session:AsyncSession, user_id: uuid.UUID) -> JobApplicationListResponse:
    result = await session.execute(select(JobApplication).where(JobApplication.user_id == user_id))
    job_applications = result.scalars().all()
    return JobApplicationListResponse(
        job_applications=[JobApplicationResponse.model_validate(job_application) for job_application in job_applications],
        total=len(job_applications)
    )

async def get_job_application_by_id(session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID) -> JobApplicationResponse:
    if not (job_application := await session.get(JobApplication, application_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
    if job_application.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this job application")
    return JobApplicationResponse.model_validate(job_application)

async def update_job_application(session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID, data: UpdateJobApplicationRequest) -> JobApplicationResponse:
    if not (job_application := await session.get(JobApplication, application_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
    if job_application.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update this job application")
    if data.status:
        job_application.status = data.status
    if data.jd_raw_text:
        job_application.jd_raw_text = data.jd_raw_text
    job_application.updated_at = datetime.now(timezone.utc)
    session.add(job_application)
    await session.commit()
    await session.refresh(job_application)
    return JobApplicationResponse.model_validate(job_application)

async def delete_job_application(session: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID) -> Dict[str, str]:
    if not (job_application := await session.get(JobApplication, application_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
    if job_application.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this job application")
    await session.delete(job_application)
    await session.commit()
    return {"message": "Job application deleted successfully"}