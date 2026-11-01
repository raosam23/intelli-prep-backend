"""Resume service: PDF text extraction and ownership checks. pdfplumber is mocked."""

import io
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from app.services.resume_service import (
    delete_resume,
    get_resume_by_id,
    get_resumes,
    update_resume,
    upload_resume,
)
from tests.factories import USER_ID, execute_result, make_resume, make_user


def _upload(name: str = "cv.pdf", payload: bytes = b"%PDF-1.4") -> UploadFile:
    return UploadFile(file=io.BytesIO(payload), filename=name)


def _patch_pdf(monkeypatch: pytest.MonkeyPatch, texts: list[str | None], error: Exception | None = None) -> None:
    if error is not None:
        monkeypatch.setattr(
            "app.services.resume_service.pdfplumber.open",
            MagicMock(side_effect=error),
        )
        return

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


@pytest.mark.asyncio
async def test_upload_resume_joins_page_text(mock_session, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pdf(monkeypatch, ["Jane Doe", None, "Python, FastAPI"])

    created = await upload_resume(mock_session, USER_ID, _upload())

    stored = mock_session.add.call_args.args[0]
    assert stored.file_name == "cv.pdf"
    assert stored.raw_text == "Jane Doe\nPython, FastAPI"
    assert stored.user_id == USER_ID
    assert created.file_name == "cv.pdf"
    assert created.parsed_json is None
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_upload_and_update_decode_parsed_json_when_the_row_has_it(
    mock_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_pdf(monkeypatch, ["Jane Doe"])

    async def _refresh(row) -> None:
        row.parsed_json = '{"skills": ["Python"]}'

    mock_session.refresh.side_effect = _refresh
    created = await upload_resume(mock_session, USER_ID, _upload())
    assert created.parsed_json == {"skills": ["Python"]}

    resume = make_resume()
    mock_session.get.return_value = resume
    updated = await update_resume(mock_session, resume.user_id, resume.id, _upload("next.pdf"))
    assert updated.parsed_json == {"skills": ["Python"]}


@pytest.mark.asyncio
async def test_upload_resume_returns_400_when_the_pdf_cannot_be_read(
    mock_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_pdf(monkeypatch, [], error=ValueError("not a pdf"))

    with pytest.raises(HTTPException) as exc_info:
        await upload_resume(mock_session, USER_ID, _upload())

    assert exc_info.value.status_code == 400
    assert "Error processing PDF" in exc_info.value.detail
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_resumes_parses_stored_json(mock_session) -> None:
    resume = make_resume(parsed_json='{"skills": ["Python"]}')
    mock_session.execute.return_value = execute_result(rows=[resume])

    listed = await get_resumes(mock_session, USER_ID)

    assert listed.total == 1
    assert listed.resumes[0].parsed_json == {"skills": ["Python"]}
    assert listed.resumes[0].file_name == "jane-doe.pdf"


@pytest.mark.asyncio
async def test_get_resume_by_id_enforces_ownership(mock_session) -> None:
    owner = make_user()
    resume = make_resume(user_id=owner.id, parsed_json='{"summary": "Backend"}')
    mock_session.get.return_value = resume

    found = await get_resume_by_id(mock_session, owner.id, resume.id)
    assert found.parsed_json == {"summary": "Backend"}

    with pytest.raises(HTTPException) as forbidden:
        await get_resume_by_id(mock_session, uuid.uuid4(), resume.id)
    assert forbidden.value.status_code == 403

    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await get_resume_by_id(mock_session, owner.id, resume.id)
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_resume_checks_the_owner_then_deletes(mock_session) -> None:
    resume = make_resume()
    mock_session.get.return_value = resume

    deleted = await delete_resume(mock_session, resume.user_id, resume.id)

    assert deleted == {"message": "Resume deleted successfully"}
    mock_session.delete.assert_awaited_once_with(resume)
    mock_session.commit.assert_awaited()

    with pytest.raises(HTTPException) as forbidden:
        await delete_resume(mock_session, uuid.uuid4(), resume.id)
    assert forbidden.value.status_code == 403

    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await delete_resume(mock_session, resume.user_id, resume.id)
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_update_resume_replaces_text_and_clears_parsed_json(
    mock_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    resume = make_resume(parsed_json='{"skills": ["old"]}')
    mock_session.get.return_value = resume
    _patch_pdf(monkeypatch, ["Updated resume"])

    updated = await update_resume(mock_session, resume.user_id, resume.id, _upload("new.pdf"))

    assert updated.file_name == "new.pdf"
    assert resume.raw_text == "Updated resume"
    assert resume.parsed_json is None
    assert updated.parsed_json is None
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_resume_rejects_missing_forbidden_and_bad_files(
    mock_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await update_resume(mock_session, USER_ID, uuid.uuid4(), _upload())
    assert missing.value.status_code == 404

    resume = make_resume()
    mock_session.get.return_value = resume
    with pytest.raises(HTTPException) as forbidden:
        await update_resume(mock_session, uuid.uuid4(), resume.id, _upload())
    assert forbidden.value.status_code == 403

    _patch_pdf(monkeypatch, [], error=ValueError("corrupt"))
    with pytest.raises(HTTPException) as bad_file:
        await update_resume(mock_session, resume.user_id, resume.id, _upload())
    assert bad_file.value.status_code == 400
