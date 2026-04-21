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
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.auth import CurrentUser
from src.config import Settings, get_settings
from src.rag.citation_extractor import CitationRef
from src.rag.generator import GeneratorResult
from src.rag.retrieval import ChunkResult
from src.routes.query import QueryRequest, QueryResponse, query_handler


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


async def test_query_happy_path(test_settings: Settings, stub_user: CurrentUser) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result()

    with _pipeline_patches([chunk], gen_result):
        response = await query_handler(
            QueryRequest(query="What is overtime pay?"),
            current_user=stub_user,
            settings=test_settings,
        )

    assert isinstance(response, QueryResponse)
    assert response.answer == "Answer [SOURCE 1]"
    assert response.model_used == "claude-haiku-4-5-20251001"
    assert "legal advice" in response.disclaimer
    assert response.query_log_id == "aaaaaaaa-0000-0000-0000-000000000001"


async def test_query_response_has_citations(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result()

    with _pipeline_patches([chunk], gen_result):
        response = await query_handler(
            QueryRequest(query="overtime?"),
            current_user=stub_user,
            settings=test_settings,
        )

    assert isinstance(response.citations, list)
    assert len(response.citations) == 1
    assert response.citations[0].source_number == 1
    assert response.citations[0].union_name == "IBEW"


async def test_r01_style_refusal_strips_spurious_citations(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunks = [
        make_chunk(union_name="United Association", text="Employer pension contributions clause."),
        make_chunk(
            union_name="Sheet Metal Workers",
            text="Employer pension contributions clause for Sheet Metal Workers.",
        ),
    ]
    gen_result = make_generator_result(
        answer=(
            "The provided documents do not contain information about pension benefits "
            "for retired Boilermakers under EPSCA agreements.\n\n"
            "The documents do address employer contributions during active employment "
            "[SOURCE 1] and [SOURCE 2], but those clauses do not describe retiree "
            "pension benefits.\n\n"
            "⚠️ This answer is for reference only and does not constitute legal advice."
        )
    )

    with _pipeline_patches(
        chunks,
        gen_result,
        known_unions=["IBEW", "United Association", "Sheet Metal Workers"],
        title_map={
            "doc-001": "United Association 2025-2030 Collective Agreement",
            "doc-002": "Sheet Metal Workers 2025-2030 Collective Agreement",
        },
    ):
        response = await query_handler(
            QueryRequest(
                query="What are the pension benefits for retired Boilermakers under EPSCA agreements?"
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert response.citations == []


async def test_same_union_partial_answer_keeps_citations(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunk = make_chunk(
        union_name="Sheet Metal Workers",
        text="Rates of pay are set out in the attached wage schedules.",
    )
    gen_result = make_generator_result(
        answer=(
            "The provided documents do not contain information about specific "
            "apprentice wage rates for Sheet Metal Workers under the 2025-2030 "
            "collective agreement.\n\n"
            "The agreement still confirms that those rates are set out in the "
            "attached wage schedules [SOURCE 1]."
        )
    )

    with _pipeline_patches(
        [chunk],
        gen_result,
        known_unions=["IBEW", "Sheet Metal Workers", "United Association"],
        title_map={"doc-001": "Sheet Metal Workers 2025-2030 Collective Agreement"},
    ):
        response = await query_handler(
            QueryRequest(
                query="What are the apprentice wage rates for Sheet Metal Workers under the 2025-2030 agreement?"
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert len(response.citations) == 1
    assert response.citations[0].union_name == "Sheet Metal Workers"


async def test_r02_refusal_without_source_markers_returns_empty_citations(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunk = make_chunk(union_name="IBEW", text="Generation grievance clause.")
    gen_result = make_generator_result(
        answer=(
            "I cannot answer this question because the provided sources do not contain "
            "information about the grievance arbitration process for IBEW Transmission "
            "workers at Bruce Power.\n\n"
            "To answer that, you would need the agreement that covers that bargaining "
            "unit and site."
        )
    )

    with _pipeline_patches(
        [chunk],
        gen_result,
        known_unions=["IBEW", "Sheet Metal Workers", "United Association"],
        title_map={"doc-001": "IBEW Generation 2025-2030 Collective Agreement"},
    ):
        response = await query_handler(
            QueryRequest(
                query="What is the grievance arbitration process for IBEW Transmission workers at Bruce Power?"
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert response.citations == []


async def test_query_log_id_none_when_db_fails(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result()

    with _pipeline_patches([chunk], gen_result, log_id=None):
        response = await query_handler(
            QueryRequest(query="overtime?"),
            current_user=stub_user,
            settings=test_settings,
        )

    assert response.query_log_id is None


def test_empty_query_returns_422(test_settings: Settings, stub_user: CurrentUser) -> None:
    del test_settings, stub_user
    with pytest.raises(ValidationError):
        QueryRequest(query="   ")


def test_whitespace_only_query_returns_422(test_settings: Settings, stub_user: CurrentUser) -> None:
    del test_settings, stub_user
    with pytest.raises(ValidationError):
        QueryRequest(query="\t\n")


async def test_cross_union_routes_to_sonnet(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunk = make_chunk()
    gen_result = make_generator_result(
        answer="Compare [SOURCE 1]", model="claude-sonnet-4-6"
    )

    mock_generate = AsyncMock(return_value=gen_result)

    with patch("src.routes.query._get_known_unions", new=AsyncMock(return_value=["IBEW"])), patch(
        "src.routes.query.retrieve", new=AsyncMock(return_value=[chunk])
    ), patch(
        "src.routes.query._get_title_map", new=AsyncMock(return_value={})
    ), patch(
        "src.routes.query.generate", new=mock_generate
    ), patch(
        "src.routes.query._write_query_log", new=AsyncMock(return_value=None)
    ):
        await query_handler(
            QueryRequest(query="Compare overtime across all unions"),
            current_user=stub_user,
            settings=test_settings,
        )

    call_kwargs = mock_generate.call_args.kwargs
    assert call_kwargs["is_cross_union"] is True


async def test_cross_union_query_passes_all_detected_unions_to_retrieval(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunks = [
        make_chunk(union_name="IBEW", text="IBEW overtime"),
        make_chunk(union_name="Sheet Metal Workers", text="Sheet Metal overtime"),
    ]
    gen_result = make_generator_result(
        answer="Compare [SOURCE 1] [SOURCE 2]",
        model="claude-sonnet-4-6",
    )

    mock_retrieve = AsyncMock(return_value=chunks)

    with patch(
        "src.routes.query._get_known_unions",
        new=AsyncMock(return_value=["IBEW", "Sheet Metal Workers"]),
    ), patch("src.routes.query.retrieve", new=mock_retrieve), patch(
        "src.routes.query._get_title_map",
        new=AsyncMock(
            return_value={
                "doc-001": "IBEW Generation 2025-2030 Collective Agreement"
            }
        ),
    ), patch(
        "src.routes.query.generate",
        new=AsyncMock(return_value=gen_result),
    ), patch(
        "src.routes.query._write_query_log",
        new=AsyncMock(return_value=None),
    ):
        await query_handler(
            QueryRequest(
                query="Compare the overtime rules for IBEW Generation and Sheet Metal Workers"
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    call_kwargs = mock_retrieve.call_args.kwargs
    assert call_kwargs["union_filters"] == ["IBEW", "Sheet Metal Workers"]


def test_missing_query_field_returns_422(test_settings: Settings, stub_user: CurrentUser) -> None:
    del test_settings, stub_user
    with pytest.raises(ValidationError):
        QueryRequest.model_validate({})
