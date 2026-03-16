import uuid
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime

class ResumeResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique identifier for the resume")
    user_id: uuid.UUID = Field(description="Unique identifier for the user")
    file_name: str = Field(description="Name of the resume file")
    parsed_json: Optional[Dict] = Field(description="Parsed JSON content of the resume", default=None)
    created_at: datetime = Field(description="Timestamp when the resume was created")
    updated_at: datetime = Field(description="Timestamp when the resume was last updated")

class ResumeListResponse(BaseModel):
    resumes: List[ResumeResponse] = Field(description="List of resumes for the user")
    total: int = Field(description="Total number of resumes for the user")