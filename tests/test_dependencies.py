"""JWT authentication dependency."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user
from app.utils.security import create_access_token
from tests.factories import make_user


@pytest.mark.asyncio
async def test_get_current_user_returns_the_token_subject(mock_session) -> None:
    user = make_user()
    token = create_access_token({"sub": str(user.id)})
    mock_session.get.return_value = user
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    resolved = await get_current_user(credentials, mock_session)

    assert resolved is user
    mock_session.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_user_rejects_an_invalid_token(mock_session) -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials, mock_session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication credentials"
    mock_session.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_current_user_rejects_an_unknown_user(mock_session) -> None:
    user = make_user()
    token = create_access_token({"sub": str(user.id)})
    mock_session.get.return_value = None
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials, mock_session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User not found"
