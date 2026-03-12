from sqlmodel import SQLModel, Field
from enum import Enum
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime

class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    APPROVED = "approved"
    REJECTED = "rejected"

class JobApplication(SQLModel, table=True):

    __tablename__ = "job_applications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    resume_id: uuid.UUID = Field(foreign_key="resumes.id", index=True)
    jd_raw_text: str
    fit_score: Optional[float] = None
    fit_breakdown_score: Optional[str] = None
    status: ApplicationStatus = Field(default=ApplicationStatus.APPLIED, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))