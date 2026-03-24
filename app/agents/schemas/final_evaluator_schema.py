from pydantic import BaseModel, Field
from typing import List
from app.models.evaluation import Verdict

class FinalEvaluatorOutput(BaseModel):
    communication_score: float = Field(description="Score for communication skills, between 0 and 100")
    technical_score: float = Field(description="Score for technical skills, between 0 and 100")
    problem_solving_score: float = Field(description="Score for problem solving skills, between 0 and 100")
    overall_score: float = Field(description="Overall score, between 0 and 100")
    verdict: Verdict = Field(description="Hiring verdict, one of: strong_hire, hire, no_decision, no_hire, strong_no_hire")
    improvement_tips: List[str] = Field(default_factory=list, description="List of specific improvement tips for the candidate based on their performance in the interview")