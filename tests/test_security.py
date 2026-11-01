"""Password hashing and JWT helpers."""

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings
from app.utils.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_and_verify_password() -> None:
    hashed = hash_password("supersecret")
    assert hashed != "supersecret"
    assert verify_password("supersecret", hashed)
    assert verify_password("wrong-password", hashed) is False


def test_each_hash_uses_a_fresh_salt() -> None:
    assert hash_password("supersecret") != hash_password("supersecret")


def test_access_token_round_trip() -> None:
    token = create_access_token({"sub": "user-1"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert "exp" in payload


def test_decode_rejects_a_tampered_token() -> None:
    token = create_access_token({"sub": "user-1"})
    assert decode_access_token(token + "tampered") is None


def test_decode_rejects_a_token_signed_with_another_secret() -> None:
    token = jwt.encode({"sub": "user-1"}, "a-different-secret", algorithm=settings.ALGORITHM)
    assert decode_access_token(token) is None


def test_decode_rejects_an_expired_token() -> None:
    expired = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "user-1", "exp": expired},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    assert decode_access_token(token) is None
