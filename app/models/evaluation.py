from sqlmodel import SQLModel, Field
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from typing import Optional
from enum import Enum

class Verdict(str, Enum):
    STRONG_HIRE = "strong_hire"
    HIRE = "hire"
    NO_DECISION = "no_decision"
    NO_HIRE = "no_hire"
    STRONG_NO_HIRE = "strong_no_hire"

class Evaluation(SQLModel, table=True):
    
    __tablename__ = "evaluations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key='interview_sessions.id', unique=True)
    communication_score: Optional[float] = None
    technical_score: Optional[float] = None
    problem_solving_score: Optional[float] = None
    overall_score: Optional[float] = None
    verdict: Verdict = Field(default=Verdict.NO_DECISION, index=True)
    improvement_tips_json: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))