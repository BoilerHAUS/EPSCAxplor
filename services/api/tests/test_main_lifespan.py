"""Lifespan wiring tests for the shared DB pool + Qdrant client (#147).

``TestClient(app)`` runs the real lifespan, so these tests assert the resources
are created on startup and torn down on shutdown without any real Postgres or
Qdrant: pool creation is lazy (``min_size=0``) and ``AsyncQdrantClient``
construction performs no I/O.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import src.db as db
import src.rag.retrieval as retrieval
from src.config import Settings
from src.main import app


def _settings(database_url: str = "postgresql://user:pass@localhost/epsca") -> Settings:
    return Settings(
        database_url=database_url,
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="test-jwt-secret-key",  # noqa: S106
    )


def test_lifespan_creates_and_closes_pool_and_qdrant_client() -> None:
    with patch("src.main.get_settings", return_value=_settings()):
        with TestClient(app):
            assert db.get_pool() is not None
            assert retrieval.get_shared_qdrant_client() is not None

        # Shutdown must release both process-wide resources.
        with pytest.raises(RuntimeError):
            db.get_pool()
        assert retrieval.get_shared_qdrant_client() is None


def test_app_boots_when_postgres_is_unreachable() -> None:
    """A briefly-down Postgres must not crash-loop the app at startup.

    The DSN points at a closed port; entering the lifespan still succeeds
    because the pool opens no connection until first acquire. /health is what
    reports the outage (covered in test_health).
    """
    unreachable = _settings(database_url="postgresql://u:p@127.0.0.1:59999/nope")
    with patch("src.main.get_settings", return_value=unreachable):
        with TestClient(app):
            assert db.get_pool() is not None
