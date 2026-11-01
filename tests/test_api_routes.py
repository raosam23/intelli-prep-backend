"""REST routes through TestClient.

Services run for real. The database session and, for protected routes, the
current user come from dependency_overrides. PDF parsing is mocked.
"""

import io
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.interview_session import DifficultyLevel, InterviewStatus, InterviewType
from app.utils.security import create_access_token, hash_password
from tests.factories import JOB_ID, SESSION_ID, execute_result, make_interview, make_job, make_resume, make_user


def _patch_pdf(monkeypatch: pytest.MonkeyPatch, texts: list[str]) -> None:
    pages = []
    for text in texts:
        page = MagicMock()
        page.extract_text.return_value = text
        pages.append(page)
    document = MagicMock()
    document.pages = pages
    document.__enter__.return_value = document
    document.__exit__.return_value = False
    monkeypatch.setattr("app.services.resume_service.pdfplumber.open", lambda *_args, **_kwargs: document)


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_and_login(client, mock_session) -> None:
    mock_session.execute.return_value = execute_result(first=None)
    registered = client.post(
        "/api/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret"},
    )
    assert registered.status_code == 200
    assert registered.json()["email"] == "ada@example.com"
    assert "hashed_password" not in registered.json()

    mock_session.execute.return_value = execute_result(first=make_user())
    duplicate = client.post(
        "/api/auth/register",
        json={"name": "Ada", "email": "test@example.com", "password": "supersecret"},
    )
    assert duplicate.status_code == 400

    invalid = client.post(
        "/api/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "short"},
    )
    assert invalid.status_code == 422

    user = make_user(hashed_password=hash_password("supersecret"))
    mock_session.execute.return_value = execute_result(first=user)
    logged_in = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "supersecret"},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["token_type"] == "bearer"
    assert logged_in.json()["access_token"]

    rejected = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "not-the-password"},
    )
    assert rejected.status_code == 401


def test_protected_routes_require_a_bearer_token(client) -> None:
    missing = client.get("/api/auth/me")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Not authenticated"
    assert client.get("/api/resumes/").status_code == 401
    assert client.get("/api/job-applications/").status_code == 401
    assert client.post("/api/interview-sessions/", json={}).status_code == 401
    assert client.get("/api/analytics/dashboard").status_code == 401


def test_me_uses_the_bearer_token(client, mock_session, mock_user) -> None:
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Invalid authentication credentials"

    token = create_access_token({"sub": str(mock_user.id)})
    mock_session.get.return_value = None
    missing = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert missing.status_code == 401
    assert missing.json()["detail"] == "User not found"

    mock_session.get.return_value = mock_user
    found = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert found.status_code == 200
    assert found.json()["email"] == mock_user.email
    assert found.json()["id"] == str(mock_user.id)


def test_update_profile(auth_client, mock_session, mock_user) -> None:
    mock_user.hashed_password = hash_password("supersecret")
    mock_session.get.return_value = mock_user

    renamed = auth_client.put("/api/auth/profile", json={"name": "Grace Hopper"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Grace Hopper"

    same_password = auth_client.put("/api/auth/profile", json={"password": "supersecret"})
    assert same_password.status_code == 400


def test_resume_routes(auth_client, mock_session, mock_user, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pdf(monkeypatch, ["Jane Doe", "Python"])

    uploaded = auth_client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["file_name"] == "resume.pdf"
    assert uploaded.json()["user_id"] == str(mock_user.id)

    monkeypatch.setattr(
        "app.services.resume_service.pdfplumber.open",
        MagicMock(side_effect=ValueError("corrupt")),
    )
    rejected = auth_client.post(
        "/api/resumes/upload",
        files={"file": ("bad.pdf", io.BytesIO(b"nope"), "application/pdf")},
    )
    assert rejected.status_code == 400

    resume = make_resume(user_id=mock_user.id, parsed_json='{"skills": ["Python"]}')
    mock_session.execute.return_value = execute_result(rows=[resume])
    listed = auth_client.get("/api/resumes/")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["resumes"][0]["parsed_json"] == {"skills": ["Python"]}

    # get_resumes decodes parsed_json on the model instance. A later request
    # loads a fresh row, so restore the stored string before the next call.
    resume.parsed_json = '{"skills": ["Python"]}'
    mock_session.get.return_value = resume
    fetched = auth_client.get(f"/api/resumes/{resume.id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == str(resume.id)

    mock_session.get.return_value = None
    missing = auth_client.get(f"/api/resumes/{uuid.uuid4()}")
    assert missing.status_code == 404

    mock_session.get.return_value = resume
    deleted = auth_client.delete(f"/api/resumes/{resume.id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"message": "Resume deleted successfully"}

    _patch_pdf(monkeypatch, ["Replaced text"])
    mock_session.get.return_value = resume
    replaced = auth_client.put(
        f"/api/resumes/{resume.id}",
        files={"new_file": ("next.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert replaced.status_code == 200
    assert replaced.json()["file_name"] == "next.pdf"


def test_job_application_routes(auth_client, mock_session, mock_user) -> None:
    resume = make_resume(user_id=mock_user.id)
    mock_session.get.return_value = resume

    created = auth_client.post(
        "/api/job-applications/",
        json={"resume_id": str(resume.id), "jd_raw_text": "Backend engineer"},
    )
    assert created.status_code == 200
    assert created.json()["status"] == "applied"
    assert created.json()["jd_raw_text"] == "Backend engineer"

    invalid = auth_client.post("/api/job-applications/", json={"jd_raw_text": "missing resume"})
    assert invalid.status_code == 422

    job = make_job(user_id=mock_user.id, resume_id=resume.id)
    mock_session.execute.return_value = execute_result(rows=[job])
    listed = auth_client.get("/api/job-applications/")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    mock_session.get.return_value = job
    fetched = auth_client.get(f"/api/job-applications/{job.id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == str(job.id)

    updated = auth_client.put(
        f"/api/job-applications/{job.id}",
        json={"status": "interviewing", "jd_raw_text": "Updated description"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "interviewing"

    mock_session.get.return_value = None
    missing = auth_client.get(f"/api/job-applications/{JOB_ID}")
    assert missing.status_code == 404

    mock_session.get.return_value = job
    deleted = auth_client.delete(f"/api/job-applications/{job.id}")
    assert deleted.status_code == 200
    assert deleted.json()["message"] == "Job application deleted successfully"


def test_interview_session_routes(auth_client, mock_session, mock_user) -> None:
    job = make_job(user_id=mock_user.id)
    mock_session.get.return_value = job

    created = auth_client.post(
        "/api/interview-sessions/",
        json={
            "job_application_id": str(job.id),
            "num_questions": 3,
            "difficulty": "senior",
            "interview_type": "behavioral",
            "focus_area": "leadership",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "pending"
    assert body["difficulty"] == "senior"
    assert body["interview_type"] == "behavioral"
    assert body["num_questions"] == 3

    too_small = auth_client.post(
        "/api/interview-sessions/",
        json={
            "job_application_id": str(job.id),
            "num_questions": 0,
            "difficulty": "mid",
            "interview_type": "mixed",
        },
    )
    assert too_small.status_code == 422

    interview = make_interview(
        job_application_id=job.id,
        difficulty=DifficultyLevel.SENIOR,
        interview_type=InterviewType.BEHAVIORAL,
        status=InterviewStatus.PENDING,
    )
    mock_session.execute.return_value = execute_result(rows=[interview])
    listed = auth_client.get(f"/api/interview-sessions/job-application/{job.id}")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["interview_sessions"][0]["id"] == str(interview.id)

    async def _get(model, _ident):
        if model.__name__ == "InterviewSession":
            return interview
        if model.__name__ == "JobApplication":
            return job
        return None

    mock_session.get.side_effect = _get
    fetched = auth_client.get(f"/api/interview-sessions/{interview.id}")
    assert fetched.status_code == 200
    assert fetched.json()["focus_area"] == interview.focus_area

    deleted = auth_client.delete(f"/api/interview-sessions/{interview.id}")
    assert deleted.status_code == 200
    assert deleted.json()["message"] == "Interview session deleted successfully"

    mock_session.get.side_effect = None
    mock_session.get.return_value = None
    missing = auth_client.get(f"/api/interview-sessions/{SESSION_ID}")
    assert missing.status_code == 404


def test_analytics_dashboard(auth_client, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = auth_client.get("/api/analytics/dashboard")
    assert empty.status_code == 200
    body = empty.json()
    assert body["overall_stats"]["total_applications"] == 0
    assert body["overall_stats"]["average_fit_score"] == 0.0
    assert body["fit_score_trend"] == []
    assert body["application_by_status"]["applied"] == 0

    def _db_error(*_args, **_kwargs):
        raise SQLAlchemyError("connection reset")

    monkeypatch.setattr("app.api.routes.analytics.get_dashboard_data", _db_error)
    failed = auth_client.get("/api/analytics/dashboard")
    assert failed.status_code == 500
    assert "connection reset" in failed.json()["detail"]

    def _unexpected(*_args, **_kwargs):
        raise RuntimeError("aggregator failed")

    monkeypatch.setattr("app.api.routes.analytics.get_dashboard_data", _unexpected)
    unexpected = auth_client.get("/api/analytics/dashboard")
    assert unexpected.status_code == 500
    assert unexpected.json()["detail"] == "aggregator failed"
