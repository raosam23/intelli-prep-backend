from pydantic import BaseModel, Field
from typing import Optional

class FollowUpDeciderOutput(BaseModel):
    follow_up_needed: bool = Field(description="A boolean value indicating whether a follow-up question is needed or not.")
    follow_up_question: Optional[str] = Field(description="If follow_up_needed is true, then follow_up_question should contain the specific follow-up question to ask the candidate. If follow_up_needed is false, then follow_up_question should be null.", default=None)