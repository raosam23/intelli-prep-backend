from typing import Optional
from sqlmodel import SQLModel, Field
import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey

class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    MANAGERIAL = "managerial"
    FOLLOWUP = "followup"

class Question(SQLModel, table=True):

    __tablename__ = "questions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    )
    question_text: str
    question_type: QuestionType = Field(index=True)
    order_index: float = Field(default=0)
    is_follow_up: bool = Field(default=False)
    follow_up_to: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=True)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))