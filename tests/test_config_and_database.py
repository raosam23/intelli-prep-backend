"""Settings defaults and the database session helpers, without a live database."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.db.database import get_session, init_db


def test_settings_defaults_when_optional_values_are_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "FromEnv")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/intelliprep")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-unit-test")
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    monkeypatch.delenv("SALT_ROUNDS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    loaded = Settings(_env_file=None)

    assert loaded.APP_NAME == "FromEnv"
    assert loaded.DEBUG is True
    assert loaded.APP_ENV == "development"
    assert loaded.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert loaded.SALT_ROUNDS == 12


def test_chat_model_is_configured_for_deterministic_interviews() -> None:
    from app.core.llm import llm

    assert llm.model_name == "gpt-4o-mini"
    assert llm.temperature == 0


@pytest.mark.asyncio
async def test_get_session_yields_the_open_session() -> None:
    fake_session = object()
    context = AsyncMock()
    context.__aenter__.return_value = fake_session
    context.__aexit__.return_value = False

    with patch("app.db.database.AsyncSession", return_value=context):
        generator = get_session()
        assert await anext(generator) is fake_session
        with pytest.raises(StopAsyncIteration):
            await anext(generator)

    context.__aexit__.assert_awaited()


@pytest.mark.asyncio
async def test_init_db_creates_tables_through_the_engine() -> None:
    connection = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = connection
    context.__aexit__.return_value = False

    with patch("app.db.database.engine") as fake_engine:
        fake_engine.begin.return_value = context
        await init_db()

    connection.run_sync.assert_awaited_once()
    assert connection.run_sync.await_args.args[0].__name__ == "create_all"
