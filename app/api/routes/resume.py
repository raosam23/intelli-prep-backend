from fastapi import APIRouter, Depends
from app.schemas.resume import ResumeListResponse, ResumeResponse 
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.resume_service import upload_resume, get_resumes, get_resume_by_id, delete_resume
from fastapi import UploadFile
from typing import Dict
import uuid


router = APIRouter()

@router.post('/upload', response_model=ResumeResponse)
async def upload_a_resume(file: UploadFile, current_user: User= Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> ResumeResponse:
    return await upload_resume(session, current_user.id, file)

@router.get('/', response_model=ResumeListResponse)
async def get_all_resumes(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> ResumeListResponse:
    return await get_resumes(session, current_user.id)

@router.get('/{resume_id}', response_model=ResumeResponse)
async def get_a_resume_by_id(resume_id: uuid.UUID, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> ResumeResponse:
    return await get_resume_by_id(session, current_user.id, resume_id)

@router.delete('/{resume_id}', response_model=Dict[str, str])
async def delete_a_resume_by_id(resume_id: uuid.UUID, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> Dict[str, str]:
    return await delete_resume(session, current_user.id, resume_id)