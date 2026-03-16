import uuid
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from app.models.job_application import ApplicationStatus
from datetime import datetime

class CreateJobApplicationRequest(BaseModel):
    resume_id: uuid.UUID = Field(description="The ID of the resume being applied with")
    jd_raw_text: str = Field(description="The raw text of the job description")

class UpdateJobApplicationRequest(BaseModel):
    status: Optional[ApplicationStatus] = Field(description="The new status of the application", default=None)
    jd_raw_text: Optional[str] = Field(description="The raw text of the job description", default=None)

class JobApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="The unique identifier of the job application")
    user_id: uuid.UUID = Field(description="The ID of the user who submitted the application")
    resume_id: uuid.UUID = Field(description="The ID of the resume being applied with")
    jd_raw_text: str = Field(description="The raw text of the job description")
    fit_score: Optional[float] = Field(description="The fit score of the application", default=None)
    fit_breakdown_score: Optional[str] = Field(description="The breakdown of the fit score by category", default=None)
    status: ApplicationStatus = Field(description="The current status of the application")
    created_at: datetime = Field(description="The timestamp when the application was created")
    updated_at: datetime = Field(description="The timestamp when the application was last updated")

class JobApplicationListResponse(BaseModel):
    job_applications: List[JobApplicationResponse] = Field(description="A list of job applications")
    total: int = Field(description="The total number of job applications")
