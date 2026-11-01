"""Install dummy settings before the application is imported.

The FastAPI app builds its settings, database engine, and ChatOpenAI client at
import time. Tests never call those services. These values are placeholders so
importing the app does not require a developer .env file or a real API key.
Existing environment variables win, which is what CI uses.
"""

import os

_DEFAULTS = {
    "APP_NAME": "IntelliPrep",
    "APP_ENV": "test",
    "DEBUG": "false",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "SECRET_KEY": "test-secret-key-for-tests-only",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "SALT_ROUNDS": "4",
    "OPENAI_API_KEY": "sk-test-key-not-used-in-tests",
}

for _key, _value in _DEFAULTS.items():
    os.environ.setdefault(_key, _value)

ENV_READY = True
