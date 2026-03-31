from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.job_application import ApplicationStatus
import uuid

class OverallStats(BaseModel):
    total_applications: int = Field(description="Total number of applications submitted")
    total_interviews_completed: int = Field(description="Total number of interviews completed")
    average_fit_score: Optional[float] = Field(description="Average fit score accross all applications", default=None)
    average_overall_score: Optional[float] = Field(description="Average overall score accross all applications", default=None)

class FitScoreTrend(BaseModel):
    job_application_id: uuid.UUID = Field(description="Unique identifier for the job application")
    fit_score: Optional[float] = Field(description="Fit score for the job application", default=None)
    created_at: datetime = Field(description="Timestamp when the job application was created by the user")
    status: ApplicationStatus = Field(description="Current status of the job application")

class InterviewPerformanceTrend(BaseModel):
    session_id: uuid.UUID = Field(description="Unique identifier for the interview session")
    communication_score: Optional[float] = Field(description="Communication score for the interview session", default=None)
    technical_score: Optional[float] = Field(description="Technical score for the interview session", default=None)
    problem_solving_score: Optional[float] = Field(description="Problem solving score for the interview session", default=None)
    overall_score: Optional[float] = Field(description="Overall score for the interview session", default=None)
    created_at: datetime = Field(description="Timestamp when the interview session was completed by the user")

class ApplicationByStatus(BaseModel):
    applied: int = Field(description="Number of applications with status 'applied'", default=0)
    interviewing: int = Field(description="Number of applications with status 'interviewing'", default=0)
    approved: int = Field(description="Number of applications with status 'approved'", default=0)
    rejected: int = Field(description="Number of applications with status 'rejected'", default=0)

class AverageScores(BaseModel):
    communication_score: Optional[float] = Field(description="Average communication score across all interview sessions", default=None)
    technical_score: Optional[float] = Field(description="Average technical score across all interview sessions", default=None)
    problem_solving_score: Optional[float] = Field(description="Average problem solving score across all interview sessions", default=None)

class DashboardResponse(BaseModel):
    overall_stats: OverallStats = Field(description="Overall statistics about the user's job applications and interviews")
    fit_score_trend: List[FitScoreTrend] = Field(description="Tred of fit score over time for the user's job applications")
    interview_performance_trend: List[InterviewPerformanceTrend] = Field(description="Trend of interview performance scores over time for the user's interview sessions")
    application_by_status: ApplicationByStatus = Field(description="Distribution of the user's job applications by their current status")
    average_scores: AverageScores = Field(description="Average scores across all interview sessions for the user")
