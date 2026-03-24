from pydantic import BaseModel, Field
from typing import List
from app.models.interview_session import InterviewType

class Question(BaseModel):
    question_text: str = Field(description="The actual interview question")
    question_type: InterviewType = Field(description="The type of the question - technical, behavioral, managerial or mixed")
    order_index: int = Field(description="The order in which the question should be asked in the interview, starting from 1 for the first question")

class QuestionGeneratorOutput(BaseModel):
    questions: List[Question] = Field(description="A list of generated interview questions")
