from app.schemas.analytics import (
    OverallStats,
    FitScoreTrend,
    InterviewPerformanceTrend,
    ApplicationByStatus,
    AverageScores,
    DashboardResponse
)
from app.models.job_application import JobApplication, ApplicationStatus
from app.models.evaluation import Evaluation
from app.models.interview_session import InterviewSession, InterviewStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, asc
from typing import Sequence
import uuid

async def get_dashboard_data(session: AsyncSession, user_id: uuid.UUID) -> DashboardResponse:
    job_application_result = await session.execute(select(JobApplication).where(JobApplication.user_id == user_id))
    completed_interview_result = await session.execute(
        select(InterviewSession).join(JobApplication).where(
            JobApplication.user_id == user_id,
            InterviewSession.status == InterviewStatus.COMPLETED
        )
    )
    job_applications: Sequence[JobApplication] = job_application_result.scalars().all()
    completed_interviews: Sequence[InterviewSession] = completed_interview_result.scalars().all()
    job_application_count = len(job_applications)
    completed_interviews_count = len(completed_interviews)
    valid_scores = [application.fit_score for application in job_applications if application.fit_score is not None]
    average_fit_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    evaluation_result = await session.execute(
        select(Evaluation)
        .join(InterviewSession)
        .join(JobApplication)
        .where(JobApplication.user_id == user_id)
    )
    evaluations: Sequence[Evaluation] = evaluation_result.scalars().all()
    valid_scores = [evaluation.overall_score for evaluation in evaluations if evaluation.overall_score is not None]
    average_overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    overall_stats = OverallStats(
        total_applications=job_application_count,
        total_interviews_completed=completed_interviews_count,
        average_fit_score=average_fit_score,
        average_overall_score=average_overall_score
    )

    job_aplication_sorted = await session.execute(
        select(JobApplication)
        .where(JobApplication.user_id == user_id)
        .order_by(asc(JobApplication.created_at))
    )
    job_applications_sorted: Sequence[JobApplication] = job_aplication_sorted.scalars().all()

    fit_score_trend = [
        FitScoreTrend(
            job_application_id=job_application.id,
            fit_score=job_application.fit_score,
            created_at=job_application.created_at,
            status=job_application.status
        )
        for job_application in job_applications_sorted
    ]

    completed_interview_evaluations_result = await session.execute(
        select(Evaluation)
        .join(InterviewSession)
        .join(JobApplication)
        .where(
            JobApplication.user_id == user_id,
            InterviewSession.status == InterviewStatus.COMPLETED
        ).order_by(asc(Evaluation.created_at))
    )
    completed_interview_evaluations: Sequence[Evaluation] = completed_interview_evaluations_result.scalars().all()
    interview_performance_trend = [
        InterviewPerformanceTrend(
            session_id=evaluation.session_id,
            communication_score=evaluation.communication_score,
            technical_score=evaluation.technical_score,
            problem_solving_score=evaluation.problem_solving_score,
            overall_score=evaluation.overall_score,
            created_at=evaluation.created_at
        )
        for evaluation in completed_interview_evaluations
    ]

    application_by_status = ApplicationByStatus(
        applied = sum(1 for application in job_applications if application.status == ApplicationStatus.APPLIED),
        interviewing= sum(1 for application in job_applications if application.status == ApplicationStatus.INTERVIEWING),
        approved = sum(1 for application in job_applications if application.status == ApplicationStatus.APPROVED),
        rejected = sum(1 for application in job_applications if application.status == ApplicationStatus.REJECTED)
    )

    valid_communication_scores = [evaluation.communication_score for evaluation in completed_interview_evaluations if evaluation.communication_score is not None]
    valid_technical_scores = [evaluation.technical_score for evaluation in completed_interview_evaluations if evaluation.technical_score is not None]
    valid_problem_solving_scores = [evaluation.problem_solving_score for evaluation in completed_interview_evaluations if evaluation.problem_solving_score is not None]

    average_scores = AverageScores(
        communication_score = sum(valid_communication_scores) / len(valid_communication_scores) if valid_communication_scores else 0.0,
        technical_score= sum(valid_technical_scores) / len(valid_technical_scores) if valid_technical_scores else 0.0,
        problem_solving_score = sum(valid_problem_solving_scores) / len(valid_problem_solving_scores) if valid_problem_solving_scores else 0.0
    )

    dashboard_response = DashboardResponse(
        overall_stats=overall_stats,
        fit_score_trend=fit_score_trend,
        interview_performance_trend=interview_performance_trend,
        application_by_status=application_by_status,
        average_scores=average_scores
    )

    return dashboard_response
