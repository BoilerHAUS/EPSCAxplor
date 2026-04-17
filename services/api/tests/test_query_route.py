"""Tests for services/api/src/routes/query.py.

Covers:
- POST /query: happy path (standard query, mock pipeline)
- POST /query: cross-union routes to Sonnet
- POST /query: empty query returns 422
- POST /query: query_log_id is None when DB write fails (best-effort)
- POST /query: response structure matches spec
- POST /query: disclaimer present in response
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.auth import CurrentUser, get_current_user
from src.config import Settings, get_settings
from src.main import app
from src.rag.citation_extractor import CitationRef
from src.rag.generator import GeneratorResult
from src.rag.retrieval import ChunkResult


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="test-jwt-secret",  # noqa: S106
    )


@pytest.fixture
def stub_user() -> CurrentUser:
    import uuid
    return CurrentUser(tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"))


def make_chunk(union_name: str = "IBEW", text: str = "Overtime clause text.") -> ChunkResult:
    return ChunkResult(
        point_id="pt-001",
        score=0.9,
        document_id="doc-001",
        source_filename="IBEW_CA.pdf",
        union_name=union_name,
        document_type="primary_ca",
        agreement_scope=None,
        effective_date="2025-05-01",
        expiry_date="2030-04-30",
        article_number="Article 12",
        article_title="Overtime",
        section_number="12.03",
        page_number=34,
        is_table=False,
        text=text,
    )


def make_generator_result(answer: str = "Answer [SOURCE 1]", model: str = "claude-haiku-4-5-20251001") -> GeneratorResult:
    return GeneratorResult(
        answer=answer,
        model_used=model,
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=250,
    )


# ─── Helper: patch full pipeline ──────────────────────────────────────────────


def _pipeline_patches(
    chunks: list[ChunkResult],
    generator_result: GeneratorResult,
    known_unions: list[str] | None = None,
    title_map: dict[str, str] | None = None,
    log_id: str | None = "aaaaaaaa-0000-0000-0000-000000000001",
) -> Any:
    """Context manager providing standard pipeline mocks."""
    from contextlib import ExitStack
    import contextlib

    @contextlib.contextmanager  # type: ignore[arg-type]
    def _stack() -> Any:
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "src.routes.query._get_known_unions",
                    new=AsyncMock(return_value=known_unions or ["IBEW", "UA"]),
                )
            )
            stack.enter_context(
                patch("src.routes.query.retrieve", new=AsyncMock(return_value=chunks))
            )
            stack.enter_context(
                patch(
                    "src.routes.query._get_title_map",
                    new=AsyncMock(return_value=title_map or {"doc-001": "IBEW CA 2025"}),
                )
            )
            stack.enter_context(
                patch("src.routes.query.generate", new=AsyncMock(return_value=generator_result))
            )
            stack.enter_context(
                patch(
                    "src.routes.query._write_query_log",
                    new=AsyncMock(return_value=log_id),
                )
            )
            yield

    return _stack()


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_query_happy_path(test_settings: Settings, stub_user: CurrentUser) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result()

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: stub_user

    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            with _pipeline_patches([chunk], gen_result):
                response = client.post("/query", json={"query": "What is overtime pay?"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Answer [SOURCE 1]"
    assert data["model_used"] == "claude-haiku-4-5-20251001"
    assert "disclaimer" in data
    assert "legal advice" in data["disclaimer"]
    assert data["query_log_id"] == "aaaaaaaa-0000-0000-0000-000000000001"


def test_query_response_has_citations(test_settings: Settings, stub_user: CurrentUser) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result()

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: stub_user

    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            with _pipeline_patches([chunk], gen_result):
                response = client.post("/query", json={"query": "overtime?"})

    app.dependency_overrides.clear()

    data = response.json()
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source_number"] == 1
    assert data["citations"][0]["union_name"] == "IBEW"


def test_query_log_id_none_when_db_fails(test_settings: Settings, stub_user: CurrentUser) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result()

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: stub_user

    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            with _pipeline_patches([chunk], gen_result, log_id=None):
                response = client.post("/query", json={"query": "overtime?"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["query_log_id"] is None


def test_empty_query_returns_422(test_settings: Settings, stub_user: CurrentUser) -> None:
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: stub_user

    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            response = client.post("/query", json={"query": "   "})

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_whitespace_only_query_returns_422(test_settings: Settings, stub_user: CurrentUser) -> None:
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: stub_user

    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            response = client.post("/query", json={"query": "\t\n"})

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_cross_union_routes_to_sonnet(test_settings: Settings, stub_user: CurrentUser) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result(
        answer="Compare [SOURCE 1]", model="claude-sonnet-4-6"
    )

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: stub_user

    mock_generate = AsyncMock(return_value=gen_result)

    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            with patch("src.routes.query._get_known_unions", new=AsyncMock(return_value=["IBEW"])), \
                 patch("src.routes.query.retrieve", new=AsyncMock(return_value=[chunk])), \
                 patch("src.routes.query._get_title_map", new=AsyncMock(return_value={})), \
                 patch("src.routes.query.generate", new=mock_generate), \
                 patch("src.routes.query._write_query_log", new=AsyncMock(return_value=None)):
                response = client.post(
                    "/query", json={"query": "Compare overtime across all unions"}
                )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    call_kwargs = mock_generate.call_args.kwargs
    assert call_kwargs["is_cross_union"] is True


def test_missing_query_field_returns_422(test_settings: Settings, stub_user: CurrentUser) -> None:
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: stub_user

    with patch("src.main.get_settings", return_value=test_settings):
        with TestClient(app) as client:
            response = client.post("/query", json={})

    app.dependency_overrides.clear()

    assert response.status_code == 422
