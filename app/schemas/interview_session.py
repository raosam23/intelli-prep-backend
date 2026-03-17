from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import uuid
from datetime import datetime
from app.models.interview_session import DifficultyLevel, InterviewType, InterviewStatus

class CreateInterviewSessionRequest(BaseModel):
    job_application_id: uuid.UUID = Field(description="The ID of the job application associated with this interview session")
    num_questions: int = Field(description="The number of questions to be asked in the interview session", ge=1)
    difficulty: DifficultyLevel = Field(description="The difficulty level of the interview session")
    interview_type: InterviewType = Field(description="The type of the interview session")
    focus_area: Optional[str] = Field(description="The specific focus area of the interview session, if applicable", default=None)

class InterviewSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="The unique identifier of the interview session")
    job_application_id: uuid.UUID = Field(description="The ID of the job application associated with this interview session")
    num_questions: int = Field(description="The number of questions to be asked in the interview session")
    difficulty: DifficultyLevel = Field(description="The difficulty level of the interview session")
    interview_type: InterviewType = Field(description="The type of the interview session")
    focus_area: Optional[str] = Field(description="The specific focus area of the interview session, if applicable", default=None)
    status: InterviewStatus = Field(description="The current status of the interview session")
    feedback: Optional[str] = Field(description="Detailed feedback from the interview session, if available", default=None)
    created_at: datetime = Field(description="The timestamp when the interview session was created")
    updated_at: datetime = Field(description="The timestamp when the interview session was last updated")

class InterviewSessionListResponse(BaseModel):
    interview_sessions: list[InterviewSessionResponse] = Field(description="A list of interview sessions")
    total: int = Field(description="The total number of interview sessions")