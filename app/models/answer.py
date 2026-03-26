from sqlmodel import SQLModel, Field
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey
from typing import Optional

class Answer(SQLModel, table=True):

    __tablename__ = "answers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    )
    session_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    )
    answer_text: Optional[str] = None
    audio_file_path: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))