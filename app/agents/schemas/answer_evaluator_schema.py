from pydantic import BaseModel, Field

class AnswerEvaluatorOutput(BaseModel):
    score: float = Field(description="A score from 0 to 100 for the candidate's answer based on how well it addresses the question, the depth of the answer, and how well it demonstrates the candidate's skills and experience.")
    feedback: str = Field(description="Feedback on what was good about the answer and what could be improved, along with actionable suggestions for improvement.")