"""Auth service behavior against a mocked session."""

import pytest
from fastapi import HTTPException

from app.schemas.auth import LoginRequest, RegisterRequest, UpdateProfileRequest
from app.services.auth_service import login_user, register_user, update_user_profile
from app.utils.security import decode_access_token, hash_password, verify_password
from tests.factories import execute_result, make_user


@pytest.mark.asyncio
async def test_register_user_persists_a_hashed_password(mock_session) -> None:
    mock_session.execute.return_value = execute_result(first=None)
    request = RegisterRequest(name="Ada Lovelace", email="ada@example.com", password="supersecret")

    created = await register_user(mock_session, request)

    stored = mock_session.add.call_args.args[0]
    assert stored.email == "ada@example.com"
    assert stored.hashed_password != "supersecret"
    assert verify_password("supersecret", stored.hashed_password)
    assert created.email == "ada@example.com"
    assert created.name == "Ada Lovelace"
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_register_user_rejects_a_duplicate_email(mock_session) -> None:
    mock_session.execute.return_value = execute_result(first=make_user())

    with pytest.raises(HTTPException) as exc_info:
        await register_user(
            mock_session,
            RegisterRequest(name="Ada", email="test@example.com", password="supersecret"),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Email already registered"
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_login_user_returns_a_token_for_the_user(mock_session) -> None:
    user = make_user(hashed_password=hash_password("supersecret"))
    mock_session.execute.return_value = execute_result(first=user)

    token = await login_user(mock_session, LoginRequest(email=user.email, password="supersecret"))

    assert token.token_type == "bearer"
    payload = decode_access_token(token.access_token)
    assert payload is not None
    assert payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_login_user_rejects_unknown_email_and_bad_password(mock_session) -> None:
    mock_session.execute.return_value = execute_result(first=None)
    with pytest.raises(HTTPException) as missing:
        await login_user(mock_session, LoginRequest(email="missing@example.com", password="supersecret"))
    assert missing.value.status_code == 401

    user = make_user(hashed_password=hash_password("supersecret"))
    mock_session.execute.return_value = execute_result(first=user)
    with pytest.raises(HTTPException) as wrong:
        await login_user(mock_session, LoginRequest(email=user.email, password="not-the-password"))
    assert wrong.value.status_code == 401
    assert wrong.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_update_profile_changes_name_and_password(mock_session) -> None:
    user = make_user(hashed_password=hash_password("supersecret"))
    mock_session.get.return_value = user

    updated = await update_user_profile(
        mock_session,
        user.id,
        UpdateProfileRequest(name="Grace Hopper", password="new-secret"),
    )

    assert updated.name == "Grace Hopper"
    assert user.name == "Grace Hopper"
    assert verify_password("new-secret", user.hashed_password)
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_profile_rejects_the_same_password_and_a_missing_user(mock_session) -> None:
    mock_session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await update_user_profile(mock_session, make_user().id, UpdateProfileRequest(name="Ada"))
    assert missing.value.status_code == 404

    user = make_user(hashed_password=hash_password("supersecret"))
    mock_session.get.return_value = user
    with pytest.raises(HTTPException) as same:
        await update_user_profile(mock_session, user.id, UpdateProfileRequest(password="supersecret"))
    assert same.value.status_code == 400
    assert same.value.detail == "New password cannot be the same as the old password"
