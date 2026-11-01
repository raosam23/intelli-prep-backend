"""Job application service ownership and status rules."""

import uuid

import pytest
from fastapi import HTTPException

from app.models.job_application import ApplicationStatus
from app.schemas.job_application import CreateJobApplicationRequest, UpdateJobApplicationRequest
from app.services.job_application_service import (
    create_job_application,
    delete_job_application,
    get_job_application_by_id,
    get_job_applications,
    update_job_application,
)
from tests.factories import USER_ID, execute_result, make_job, make_resume


@pytest.mark.asyncio
async def test_create_job_application_requires_an_owned_resume(mock_session) -> None:
    resume = make_resume(user_id=USER_ID)
    mock_session.get.return_value = resume
    request = CreateJobApplicationRequest(resume_id=resume.id, jd_raw_text="API platform role")

    created = await create_job_application(mock_session, USER_ID, request)

    stored = mock_session.add.call_args.args[0]
    assert stored.user_id == USER_ID
    assert stored.resume_id == resume.id
    assert stored.status == ApplicationStatus.APPLIED
    assert created.jd_raw_text == "API platform role"
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_job_application_rejects_missing_or_foreign_resumes(mock_session) -> None:
    mock_session.get.return_value = None
    request = CreateJobApplicationRequest(resume_id=uuid.uuid4(), jd_raw_text="Role")
    with pytest.raises(HTTPException) as missing:
        await create_job_application(mock_session, USER_ID, request)
    assert missing.value.status_code == 404

    mock_session.get.return_value = make_resume(user_id=uuid.uuid4())
    with pytest.raises(HTTPException) as forbidden:
        await create_job_application(mock_session, USER_ID, request)
    assert forbidden.value.status_code == 403
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_list_and_get_job_applications(mock_session) -> None:
    owned = make_job(user_id=USER_ID, fit_score=81.0)
    mock_session.execute.return_value = execute_result(rows=[owned])

    listed = await get_job_applications(mock_session, USER_ID)
    assert listed.total == 1
    assert listed.job_applications[0].fit_score == 81.0

    mock_session.get.return_value = owned
    found = await get_job_application_by_id(mock_session, USER_ID, owned.id)
    assert found.id == owned.id

    with pytest.raises(HTTPException) as forbidden:
        await get_job_application_by_id(mock_session, uuid.uuid4(), owned.id)
    assert forbidden.value.status_code == 403

    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await get_job_application_by_id(mock_session, USER_ID, owned.id)
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_update_job_application_applies_only_provided_fields(mock_session) -> None:
    job = make_job(jd_raw_text="original", status=ApplicationStatus.APPLIED)
    mock_session.get.return_value = job

    unchanged = await update_job_application(
        mock_session,
        USER_ID,
        job.id,
        UpdateJobApplicationRequest(),
    )
    assert unchanged.jd_raw_text == "original"
    assert job.status == ApplicationStatus.APPLIED

    blank = await update_job_application(
        mock_session,
        USER_ID,
        job.id,
        UpdateJobApplicationRequest(jd_raw_text=""),
    )
    assert blank.jd_raw_text == "original"

    updated = await update_job_application(
        mock_session,
        USER_ID,
        job.id,
        UpdateJobApplicationRequest(status=ApplicationStatus.INTERVIEWING, jd_raw_text="rewritten"),
    )
    assert updated.status == ApplicationStatus.INTERVIEWING
    assert job.jd_raw_text == "rewritten"


@pytest.mark.asyncio
async def test_update_and_delete_enforce_ownership(mock_session) -> None:
    job = make_job()
    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing_update:
        await update_job_application(mock_session, USER_ID, job.id, UpdateJobApplicationRequest(jd_raw_text="x"))
    assert missing_update.value.status_code == 404

    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing_delete:
        await delete_job_application(mock_session, USER_ID, job.id)
    assert missing_delete.value.status_code == 404

    mock_session.get.return_value = job
    with pytest.raises(HTTPException) as forbidden_update:
        await update_job_application(
            mock_session,
            uuid.uuid4(),
            job.id,
            UpdateJobApplicationRequest(status=ApplicationStatus.REJECTED),
        )
    assert forbidden_update.value.status_code == 403

    with pytest.raises(HTTPException) as forbidden_delete:
        await delete_job_application(mock_session, uuid.uuid4(), job.id)
    assert forbidden_delete.value.status_code == 403

    deleted = await delete_job_application(mock_session, USER_ID, job.id)
    assert deleted == {"message": "Job application deleted successfully"}
    mock_session.delete.assert_awaited_once_with(job)
