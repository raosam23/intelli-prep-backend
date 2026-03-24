from pydantic import BaseModel, Field

class FitBreakdownScore(BaseModel):
    technical_skills_match: float = Field(description="The score for technical skills match, on a scale from 0 to 100")
    experience_match: float = Field(description="The score for experience match, on a scale from 0 to 100")
    education_match: float = Field(description="The score for education match, on a scale from 0 to 100")

class FitScorerOutput(BaseModel):
    fit_score: float = Field(description="The overall fit score indicating how well the candidate's resume matches the job description, on a scale from 0 to 100")
    fit_breakdown_score: FitBreakdownScore = Field(description="The breakdown of the fit score into technical skills match, experience match, and education match")
