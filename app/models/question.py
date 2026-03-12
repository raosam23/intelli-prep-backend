from typing import Optional
from sqlmodel import SQLModel, Field
import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime

class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    MANAGERIAL = "managerial"
    FOLLOWUP = "followup"

class Question(SQLModel, table=True):

    __tablename__ = "questions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="interview_sessions.id")
    question_text: str
    question_type: QuestionType = Field(index=True)
    order_index: int = Field(default=0)
    is_follow_up: bool = Field(default=False)
    follow_up_to: Optional[uuid.UUID] = Field(default=None, foreign_key="questions.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))