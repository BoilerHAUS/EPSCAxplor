import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# src.main builds its FastAPI ``app`` at import time via ``create_app()``, which
# resolves Settings to read the CORS allow-list from a single source (#146).
# That requires the core env vars below, so set safe dummy defaults *before*
# importing the app to keep env-less test runs / CI green. ``setdefault`` means
# a real environment or per-test overrides still take precedence.
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/epsca")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key")

from src.config import Settings, get_settings  # noqa: E402
from src.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    """Prevent lru_cache from leaking real Settings across tests."""
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="test-jwt-secret-key",  # noqa: S106
    )


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_settings] = lambda: test_settings
    # Also patch the direct call in lifespan (bypasses FastAPI dependency injection)
    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()
