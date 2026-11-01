"""Builders for SQLModel rows and LangGraph state used across the suite."""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

from app.models.interview_session import (
    DifficultyLevel,
    InterviewSession,
    InterviewStatus,
    InterviewType,
)
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.resume import Resume
from app.models.user import User

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
RESUME_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
JOB_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
SESSION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def make_user(**overrides: Any) -> User:
    data: dict[str, Any] = {
        "id": USER_ID,
        "email": "test@example.com",
        "name": "Test User",
        "hashed_password": "hashed-password",
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return User(**data)


def make_resume(**overrides: Any) -> Resume:
    data: dict[str, Any] = {
        "id": RESUME_ID,
        "user_id": USER_ID,
        "file_name": "jane-doe.pdf",
        "raw_text": "Jane Doe\nBackend engineer",
        "parsed_json": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return Resume(**data)


def make_job(**overrides: Any) -> JobApplication:
    data: dict[str, Any] = {
        "id": JOB_ID,
        "user_id": USER_ID,
        "resume_id": RESUME_ID,
        "jd_raw_text": "Backend engineer who can design APIs",
        "fit_score": None,
        "fit_breakdown_score": None,
        "status": ApplicationStatus.APPLIED,
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return JobApplication(**data)


def make_interview(**overrides: Any) -> InterviewSession:
    data: dict[str, Any] = {
        "id": SESSION_ID,
        "job_application_id": JOB_ID,
        "num_questions": 3,
        "difficulty": DifficultyLevel.MID,
        "interview_type": InterviewType.MIXED,
        "focus_area": "system design",
        "status": InterviewStatus.PENDING,
        "feedback": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return InterviewSession(**data)


def execute_result(first: Any = None, rows: list[Any] | None = None) -> MagicMock:
    """Mimic the SQLAlchemy result object the services actually use."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = first
    scalars.all.return_value = [] if rows is None else rows
    result.scalars.return_value = scalars
    result.scalar_one_or_none.return_value = first
    return result


def interview_state(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "session_id": str(SESSION_ID),
        "user_id": str(USER_ID),
        "job_application_id": str(JOB_ID),
        "raw_resume": "Jane Doe, backend engineer. Skills: Python, FastAPI.",
        "parsed_resume": {"skills": ["Python", "FastAPI"], "summary": "Backend engineer"},
        "jd_raw_text": "We are hiring a backend engineer with API design experience.",
        "parsed_jd": {"required_skills": ["Python"], "job_title": "Backend Engineer"},
        "fit_score": 0.0,
        "fit_breakdown_score": {},
        "num_questions": 2,
        "difficulty": "mid",
        "interview_type": "technical",
        "focus_area": None,
        "questions": [
            {
                "question_text": "How would you design a rate limiter?",
                "question_type": "technical",
                "order_index": 1,
            },
            {
                "question_text": "How do you test a FastAPI service?",
                "question_type": "technical",
                "order_index": 2,
            },
        ],
        "current_question_index": 0,
        "current_question": {},
        "answers": [],
        "follow_up_count": 0,
        "final_evaluation": {},
        "is_complete": False,
        "error": None,
    }
    state.update(overrides)
    return state
