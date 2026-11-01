"""Dashboard aggregation. Queries are mocked; the arithmetic is real."""

import uuid
from datetime import datetime, timezone

import pytest

from app.models.evaluation import Evaluation, Verdict
from app.models.interview_session import InterviewStatus
from app.models.job_application import ApplicationStatus
from app.services.analytics_service import get_dashboard_data
from tests.factories import USER_ID, execute_result, make_interview, make_job


def _evaluation(session_id: uuid.UUID, created_at: datetime, **scores) -> Evaluation:
    data = {
        "session_id": session_id,
        "communication_score": None,
        "technical_score": None,
        "problem_solving_score": None,
        "overall_score": None,
        "verdict": Verdict.NO_DECISION,
        "created_at": created_at,
    }
    data.update(scores)
    return Evaluation(**data)


@pytest.mark.asyncio
async def test_dashboard_is_empty_when_the_user_has_no_data(mock_session) -> None:
    dashboard = await get_dashboard_data(mock_session, USER_ID)

    assert dashboard.overall_stats.total_applications == 0
    assert dashboard.overall_stats.total_interviews_completed == 0
    assert dashboard.overall_stats.average_fit_score == 0.0
    assert dashboard.overall_stats.average_overall_score == 0.0
    assert dashboard.fit_score_trend == []
    assert dashboard.interview_performance_trend == []
    assert dashboard.application_by_status.applied == 0
    assert dashboard.average_scores.communication_score == 0.0
    assert dashboard.average_scores.technical_score == 0.0
    assert dashboard.average_scores.problem_solving_score == 0.0


@pytest.mark.asyncio
async def test_dashboard_averages_ignore_missing_scores_and_counts_statuses(mock_session) -> None:
    january = datetime(2026, 1, 1, tzinfo=timezone.utc)
    february = datetime(2026, 2, 1, tzinfo=timezone.utc)
    applications = [
        make_job(fit_score=80, status=ApplicationStatus.APPLIED, created_at=january),
        make_job(id=uuid.uuid4(), fit_score=None, status=ApplicationStatus.REJECTED, created_at=february),
        make_job(id=uuid.uuid4(), fit_score=60, status=ApplicationStatus.APPROVED, created_at=february),
        make_job(id=uuid.uuid4(), fit_score=100, status=ApplicationStatus.INTERVIEWING, created_at=january),
    ]
    completed = [
        make_interview(status=InterviewStatus.COMPLETED),
        make_interview(id=uuid.uuid4(), status=InterviewStatus.COMPLETED),
    ]
    evaluations = [
        _evaluation(
            completed[0].id,
            january,
            communication_score=80,
            technical_score=70,
            problem_solving_score=60,
            overall_score=75,
            verdict=Verdict.HIRE,
        ),
        _evaluation(
            completed[1].id,
            february,
            technical_score=90,
        ),
    ]
    mock_session.execute.side_effect = [
        execute_result(rows=applications),
        execute_result(rows=completed),
        execute_result(rows=evaluations),
        execute_result(rows=applications),
        execute_result(rows=evaluations),
    ]

    dashboard = await get_dashboard_data(mock_session, USER_ID)

    assert dashboard.overall_stats.total_applications == 4
    assert dashboard.overall_stats.total_interviews_completed == 2
    assert dashboard.overall_stats.average_fit_score == 80
    assert dashboard.overall_stats.average_overall_score == 75
    assert dashboard.application_by_status.applied == 1
    assert dashboard.application_by_status.rejected == 1
    assert dashboard.application_by_status.approved == 1
    assert dashboard.application_by_status.interviewing == 1
    assert dashboard.average_scores.communication_score == 80
    assert dashboard.average_scores.technical_score == 80
    assert dashboard.average_scores.problem_solving_score == 60
    assert [point.job_application_id for point in dashboard.fit_score_trend] == [
        application.id for application in applications
    ]
    assert dashboard.fit_score_trend[1].fit_score is None
    assert dashboard.interview_performance_trend[0].overall_score == 75
    assert dashboard.interview_performance_trend[1].overall_score is None
    assert dashboard.interview_performance_trend[1].technical_score == 90
