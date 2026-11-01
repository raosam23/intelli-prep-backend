"""Shared fixtures.

External systems are replaced here: the async database session, the authenticated
user, and FastAPI dependency overrides. LLM calls are patched in the tests that
exercise agent nodes. No test needs a network connection or a real API key.
"""

from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.bootstrap import ENV_READY
from tests.factories import make_user

from app.api.dependencies import get_current_user
from app.db.database import get_session
from app.main import app
from app.models.user import User


def pytest_configure(config: pytest.Config) -> None:
    if not ENV_READY:
        raise RuntimeError("test environment was not initialised")


@pytest.fixture
def mock_user() -> User:
    """Authenticated user returned by the auth dependency override."""
    return make_user()


@pytest.fixture
def mock_session() -> AsyncMock:
    """AsyncSession double with the methods the services call."""
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalars.return_value.first.return_value = None
    result.scalar_one_or_none.return_value = None
    result.all.return_value = []

    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def client(mock_session: AsyncMock) -> Iterator[TestClient]:
    """TestClient whose database dependency is the mock session.

    Startup does not connect to Postgres: the lifespan init_db hook is patched.
    """

    async def _get_session() -> AsyncIterator[AsyncMock]:
        yield mock_session

    app.dependency_overrides[get_session] = _get_session
    try:
        with patch("app.main.init_db", new_callable=AsyncMock):
            with TestClient(app) as test_client:
                yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client: TestClient, mock_user: User) -> TestClient:
    """TestClient that is already authenticated as mock_user."""

    async def _current_user() -> User:
        return mock_user

    app.dependency_overrides[get_current_user] = _current_user
    return client
