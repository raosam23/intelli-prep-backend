import uuid
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Resume
from app.schemas.resume import ResumeResponse, ResumeListResponse
import pdfplumber
import io
import json
from sqlmodel import select
from typing import Dict

async def upload_resume(session: AsyncSession, user_id: uuid.UUID, file: UploadFile) -> ResumeResponse:
    file_bytes = await file.read()
    file_like = io.BytesIO(file_bytes)
    try:
        with pdfplumber.open(file_like) as pdf:
            all_text = []
            for page in pdf.pages:
                if text:= page.extract_text():
                    all_text.append(text)
        raw_text = "\n".join(all_text)
        resume = Resume(
            user_id=user_id,
            file_name=file.filename,
            raw_text=raw_text
        )
        session.add(resume)
        await session.commit()
        await session.refresh(resume)
        if resume.parsed_json:
            resume.parsed_json = json.loads(resume.parsed_json)
        return ResumeResponse.model_validate(resume)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error processing PDF: {str(e)}")

async def get_resumes(session: AsyncSession, user_id: uuid.UUID) -> ResumeListResponse:
    def convert_resumes(resume: Resume) -> ResumeResponse:
        if resume.parsed_json:
            resume.parsed_json = json.loads(resume.parsed_json)
        return ResumeResponse.model_validate(resume)
    get_resumes_query = await session.execute(
        select(Resume).where(Resume.user_id == user_id)
    )
    resumes = get_resumes_query.scalars().all()
    return ResumeListResponse(
        resumes=[convert_resumes(resume) for resume in resumes],
        total=len(resumes)
    )

async def get_resume_by_id(session: AsyncSession, user_id: uuid.UUID, resume_id: uuid.UUID) -> ResumeResponse:
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resume")
    if resume.parsed_json:
        resume.parsed_json = json.loads(resume.parsed_json)
    return ResumeResponse.model_validate(resume)


async def delete_resume(session: AsyncSession, user_id: uuid.UUID, resume_id: uuid.UUID) -> Dict[str, str]:
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this resume")
    await session.delete(resume)
    await session.commit()
    return {"message": "Resume deleted successfully"}