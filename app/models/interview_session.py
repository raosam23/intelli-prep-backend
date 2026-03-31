from sqlmodel import SQLModel, Field
import uuid
from enum import Enum
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey


class DifficultyLevel(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"

class InterviewType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    MANAGERIAL = "managerial"
    MIXED = "mixed"

class InterviewStatus(str, Enum):
    PENDING = "pending"
    INPROGRESS = "in_progress"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"


class InterviewSession(SQLModel, table=True):

    __tablename__ = "interview_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    job_application_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    num_questions: int
    difficulty: DifficultyLevel = Field(index=True)
    interview_type: InterviewType = Field(index=True)
    focus_area: Optional[str] = None
    status: InterviewStatus = Field(default=InterviewStatus.PENDING, index=True)
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))