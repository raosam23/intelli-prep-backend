"""Interview session service: ownership, listing, and which statuses can be deleted."""

import uuid

import pytest
from fastapi import HTTPException

from app.models.interview_session import DifficultyLevel, InterviewStatus, InterviewType
from app.schemas.interview_session import CreateInterviewSessionRequest
from app.services.interview_session_service import (
    create_interview_session,
    delete_interview_session,
    get_interview_session_by_id,
    get_interview_sessions_by_job_application,
)
from tests.factories import execute_result, make_interview, make_job, make_user


def _lookup(*rows):
    async def _get(model, _ident):
        for row in rows:
            if isinstance(row, model):
                return row
        return None

    return _get


@pytest.mark.asyncio
async def test_create_interview_session_starts_pending(mock_session) -> None:
    user = make_user()
    job = make_job(user_id=user.id)
    mock_session.get.side_effect = _lookup(job)
    request = CreateInterviewSessionRequest(
        job_application_id=job.id,
        num_questions=4,
        difficulty=DifficultyLevel.JUNIOR,
        interview_type=InterviewType.TECHNICAL,
        focus_area="testing",
    )

    created = await create_interview_session(mock_session, user, request)

    stored = mock_session.add.call_args.args[0]
    assert stored.status == InterviewStatus.PENDING
    assert stored.num_questions == 4
    assert stored.focus_area == "testing"
    assert created.difficulty == DifficultyLevel.JUNIOR
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_interview_session_rejects_missing_or_foreign_jobs(mock_session) -> None:
    user = make_user()
    request = CreateInterviewSessionRequest(
        job_application_id=uuid.uuid4(),
        num_questions=1,
        difficulty=DifficultyLevel.MID,
        interview_type=InterviewType.MIXED,
    )
    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await create_interview_session(mock_session, user, request)
    assert missing.value.status_code == 404

    mock_session.get.return_value = make_job(user_id=uuid.uuid4())
    with pytest.raises(HTTPException) as forbidden:
        await create_interview_session(mock_session, user, request)
    assert forbidden.value.status_code == 403
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_list_sessions_for_an_owned_job_application(mock_session) -> None:
    user = make_user()
    job = make_job(user_id=user.id)
    session_row = make_interview(job_application_id=job.id)
    mock_session.get.side_effect = _lookup(job)
    mock_session.execute.return_value = execute_result(rows=[session_row])

    listed = await get_interview_sessions_by_job_application(mock_session, user, job.id)

    assert listed.total == 1
    assert listed.interview_sessions[0].id == session_row.id


@pytest.mark.asyncio
async def test_list_sessions_checks_the_job_application(mock_session) -> None:
    user = make_user()
    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await get_interview_sessions_by_job_application(mock_session, user, uuid.uuid4())
    assert missing.value.status_code == 404

    mock_session.get.return_value = make_job(user_id=uuid.uuid4())
    with pytest.raises(HTTPException) as forbidden:
        await get_interview_sessions_by_job_application(mock_session, user, uuid.uuid4())
    assert forbidden.value.status_code == 403


@pytest.mark.asyncio
async def test_get_interview_session_requires_the_parent_job(mock_session) -> None:
    user = make_user()
    interview = make_interview()
    job = make_job(id=interview.job_application_id, user_id=user.id)
    mock_session.get.side_effect = _lookup(interview, job)

    found = await get_interview_session_by_id(mock_session, user, interview.id)
    assert found.id == interview.id

    mock_session.get.side_effect = _lookup(interview)
    with pytest.raises(HTTPException) as orphan:
        await get_interview_session_by_id(mock_session, user, interview.id)
    assert orphan.value.status_code == 404
    assert orphan.value.detail == "Associated job application not found"

    foreign_job = make_job(id=interview.job_application_id, user_id=uuid.uuid4())
    mock_session.get.side_effect = _lookup(interview, foreign_job)
    with pytest.raises(HTTPException) as forbidden:
        await get_interview_session_by_id(mock_session, user, interview.id)
    assert forbidden.value.status_code == 403

    mock_session.get.return_value = None
    mock_session.get.side_effect = None
    with pytest.raises(HTTPException) as missing:
        await get_interview_session_by_id(mock_session, user, interview.id)
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_checks_the_session_and_the_parent_job(mock_session) -> None:
    user = make_user()
    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await delete_interview_session(mock_session, user, uuid.uuid4())
    assert missing.value.status_code == 404
    assert missing.value.detail == "Interview session not found"

    interview = make_interview()
    mock_session.get.side_effect = _lookup(interview)
    with pytest.raises(HTTPException) as orphan:
        await delete_interview_session(mock_session, user, interview.id)
    assert orphan.value.status_code == 404
    assert orphan.value.detail == "Associated job application not found"

    foreign_job = make_job(id=interview.job_application_id, user_id=uuid.uuid4())
    mock_session.get.side_effect = _lookup(interview, foreign_job)
    with pytest.raises(HTTPException) as forbidden:
        await delete_interview_session(mock_session, user, interview.id)
    assert forbidden.value.status_code == 403


@pytest.mark.parametrize("status", [InterviewStatus.PENDING, InterviewStatus.INCOMPLETE])
@pytest.mark.asyncio
async def test_delete_allows_pending_and_incomplete_sessions(mock_session, status: InterviewStatus) -> None:
    user = make_user()
    interview = make_interview(status=status)
    job = make_job(id=interview.job_application_id, user_id=user.id)
    mock_session.get.side_effect = _lookup(interview, job)

    deleted = await delete_interview_session(mock_session, user, interview.id)

    assert deleted == {"message": "Interview session deleted successfully"}
    mock_session.delete.assert_awaited_once_with(interview)


@pytest.mark.parametrize("status", [InterviewStatus.INPROGRESS, InterviewStatus.COMPLETED])
@pytest.mark.asyncio
async def test_delete_rejects_sessions_that_have_started(mock_session, status: InterviewStatus) -> None:
    user = make_user()
    interview = make_interview(status=status)
    job = make_job(id=interview.job_application_id, user_id=user.id)
    mock_session.get.side_effect = _lookup(interview, job)

    with pytest.raises(HTTPException) as exc_info:
        await delete_interview_session(mock_session, user, interview.id)

    assert exc_info.value.status_code == 400
    assert "Only pending or incomplete" in exc_info.value.detail
    mock_session.delete.assert_not_awaited()
