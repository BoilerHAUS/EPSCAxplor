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
from src.rag.condense import (
    MAX_HISTORY_TURNS,
    PER_TURN_CHAR_CAP,
    TOTAL_HISTORY_CHAR_BUDGET,
)
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
    condensed: str | None = None,
) -> Any:
    """Context manager providing standard pipeline mocks.

    When ``condensed`` is given, the condense step is stubbed to return it (used
    by multi-turn tests). When ``None`` the real ``condense_query`` runs and — on
    the empty default history — short-circuits without any LLM call, so existing
    single-turn tests keep exercising the unchanged path.
    """
    from contextlib import ExitStack
    import contextlib

    @contextlib.contextmanager  # type: ignore[arg-type]
    def _stack() -> Any:
        with ExitStack() as stack:
            if condensed is not None:
                stack.enter_context(
                    patch(
                        "src.routes.query.condense_query",
                        new=AsyncMock(return_value=condensed),
                    )
                )
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


async def test_r01_partially_grounded_refusal_keeps_cited_sources(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    """#119: an answer that opens with a refusal phrase but still cites
    resolvable [SOURCE N] markers is partially grounded — those citations must
    be kept.

    This exact shape was stripped under #57; #119 reverses that so a working
    retrieval is never made to look broken (zero citations). Pure refusals with
    no source markers still yield empty citations — see
    test_r02_refusal_without_source_markers_returns_empty_citations and
    test_pure_refusal_without_markers_still_returns_no_citations.
    """
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

    assert [c.source_number for c in response.citations] == [1, 2]
    assert response.citations[0].union_name == "United Association"
    assert response.citations[1].union_name == "Sheet Metal Workers"


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


async def test_r03_nuclear_refusal_with_source_marker_keeps_citation(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    """#119 regression (live prod evidence, 2026-07-17).

    A union-less nuclear query whose answer opens with a refusal but cites a
    resolvable [SOURCE N] must keep that citation instead of returning zero.
    The same query *with a union named* already worked (union_filters path);
    this locks the union-less path.
    """
    chunk = make_chunk(
        union_name="Labourers",
        text="Shift differentials for Labourers are set out in Article 27.",
    )
    gen_result = make_generator_result(
        answer=(
            "The provided documents do not contain information about shift premiums "
            "for Bruce Power nuclear work.\n\n"
            "The only shift differential information in the provided documents appears "
            "in [SOURCE 1], which covers Labourers shift differentials under Article 27, "
            "but this does not reference Bruce Power specifically."
        )
    )

    with _pipeline_patches(
        [chunk],
        gen_result,
        known_unions=["IBEW", "Sheet Metal Workers", "United Association", "Labourers"],
        title_map={"doc-001": "Labourers 2025-2030 Collective Agreement"},
    ):
        response = await query_handler(
            QueryRequest(query="What are the shift premiums for Bruce Power nuclear work?"),
            current_user=stub_user,
            settings=test_settings,
        )

    assert len(response.citations) == 1
    assert response.citations[0].source_number == 1
    assert response.citations[0].union_name == "Labourers"


async def test_pure_refusal_without_markers_still_returns_no_citations(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    """#57 intent preserved: a union-less pure refusal with no [SOURCE N]
    markers still yields empty citations — there is nothing grounded to cite."""
    chunk = make_chunk(union_name="United Association", text="Some unrelated clause.")
    gen_result = make_generator_result(
        answer=(
            "The provided documents do not contain information about parental leave "
            "top-up for Boilermakers.\n\n"
            "You would need the agreement covering that bargaining unit to answer this."
        )
    )

    with _pipeline_patches(
        [chunk],
        gen_result,
        known_unions=["IBEW", "United Association", "Sheet Metal Workers"],
        title_map={"doc-001": "United Association 2025-2030 Collective Agreement"},
    ):
        response = await query_handler(
            QueryRequest(query="What is the parental leave top-up for Boilermakers?"),
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


# ─── structured rate lookup wiring (issue #89) ───────────────────────────────


async def test_rate_query_passes_rate_classification_to_retrieval(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    chunks = [make_chunk()]
    mock_retrieve = AsyncMock(return_value=chunks)

    with patch(
        "src.routes.query._get_known_unions",
        new=AsyncMock(return_value=["Labourers"]),
    ), patch("src.routes.query.retrieve", new=mock_retrieve), patch(
        "src.routes.query._get_title_map",
        new=AsyncMock(return_value={}),
    ), patch(
        "src.routes.query.generate",
        new=AsyncMock(return_value=make_generator_result()),
    ), patch(
        "src.routes.query._write_query_log",
        new=AsyncMock(return_value=None),
    ):
        await query_handler(
            QueryRequest(
                query="What is the journeyperson rate for Labourers in Windsor?"
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert mock_retrieve.call_args.kwargs["rate_classification"] == "journeyman"


async def test_pinned_chunk_sets_has_pinned_rate_on_generate(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    pinned_chunk = make_chunk().model_copy(update={"pinned": True})
    mock_generate = AsyncMock(return_value=make_generator_result())

    with patch(
        "src.routes.query._get_known_unions",
        new=AsyncMock(return_value=["Labourers"]),
    ), patch(
        "src.routes.query.retrieve",
        new=AsyncMock(return_value=[pinned_chunk]),
    ), patch(
        "src.routes.query._get_title_map",
        new=AsyncMock(return_value={}),
    ), patch("src.routes.query.generate", new=mock_generate), patch(
        "src.routes.query._write_query_log",
        new=AsyncMock(return_value=None),
    ):
        await query_handler(
            QueryRequest(
                query="What is the journeyperson rate for Labourers in Windsor?"
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert mock_generate.call_args.kwargs["has_pinned_rate"] is True


async def test_unpinned_chunks_leave_has_pinned_rate_false(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    mock_generate = AsyncMock(return_value=make_generator_result())

    with patch(
        "src.routes.query._get_known_unions",
        new=AsyncMock(return_value=["IBEW"]),
    ), patch(
        "src.routes.query.retrieve",
        new=AsyncMock(return_value=[make_chunk()]),
    ), patch(
        "src.routes.query._get_title_map",
        new=AsyncMock(return_value={}),
    ), patch("src.routes.query.generate", new=mock_generate), patch(
        "src.routes.query._write_query_log",
        new=AsyncMock(return_value=None),
    ):
        await query_handler(
            QueryRequest(query="What are the overtime rules for IBEW?"),
            current_user=stub_user,
            settings=test_settings,
        )

    assert mock_generate.call_args.kwargs["has_pinned_rate"] is False


# ─── conversational memory: history validation (issue #167) ──────────────────


def test_history_defaults_to_empty_list() -> None:
    # The eval harness and every current caller POST {"query": ...} with no
    # history; the field must default to [] so that path is byte-for-byte intact.
    req = QueryRequest(query="What is overtime?")
    assert req.history == []


def test_history_within_bounds_accepted() -> None:
    req = QueryRequest.model_validate(
        {
            "query": "what about the boilermakers?",
            "history": [
                {"role": "user", "content": "What is the foreman rate for all unions?"},
                {"role": "assistant", "content": "Rates vary by union..."},
            ],
        }
    )
    assert [t.role for t in req.history] == ["user", "assistant"]
    assert req.history[0].content == "What is the foreman rate for all unions?"


def test_history_too_many_turns_rejected() -> None:
    hist = [{"role": "user", "content": "q"} for _ in range(MAX_HISTORY_TURNS + 1)]
    with pytest.raises(ValidationError):
        QueryRequest.model_validate({"query": "x", "history": hist})


def test_history_oversized_total_rejected() -> None:
    # Each turn is under the per-turn cap, but together they exceed the total
    # budget — isolates the aggregate-budget validator from the per-turn cap.
    per = (TOTAL_HISTORY_CHAR_BUDGET // MAX_HISTORY_TURNS) + 1
    assert per <= PER_TURN_CHAR_CAP  # guard: stays under the per-turn cap
    hist = [{"role": "user", "content": "x" * per} for _ in range(MAX_HISTORY_TURNS)]
    with pytest.raises(ValidationError):
        QueryRequest.model_validate({"query": "x", "history": hist})


def test_history_oversized_single_turn_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(
            {
                "query": "x",
                "history": [{"role": "user", "content": "x" * (PER_TURN_CHAR_CAP + 1)}],
            }
        )


def test_history_invalid_role_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(
            {"query": "x", "history": [{"role": "system", "content": "hi"}]}
        )


def test_valid_multi_exchange_history_accepted() -> None:
    req = QueryRequest.model_validate(
        {
            "query": "and the apprentice rate?",
            "history": [
                {"role": "user", "content": "IBEW journeyperson rate?"},
                {"role": "assistant", "content": "$54.30/hr [SOURCE 1]."},
                {"role": "user", "content": "what about foreman?"},
                {"role": "assistant", "content": "A 15% premium [SOURCE 1]."},
            ],
        }
    )
    assert len(req.history) == 4


def test_history_starting_with_assistant_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(
            {
                "query": "x",
                "history": [
                    {"role": "assistant", "content": "a"},
                    {"role": "user", "content": "q"},
                ],
            }
        )


def test_history_non_alternating_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(
            {
                "query": "x",
                "history": [
                    {"role": "user", "content": "q1"},
                    {"role": "user", "content": "q2"},
                ],
            }
        )


def test_history_ending_with_user_rejected() -> None:
    # Odd-length, user-first, alternating — but appending the current user turn
    # would create two consecutive user turns (Anthropic 400). Must be rejected.
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(
            {
                "query": "x",
                "history": [
                    {"role": "user", "content": "q1"},
                    {"role": "assistant", "content": "a1"},
                    {"role": "user", "content": "q2"},
                ],
            }
        )


# ─── conversational memory: pipeline wiring (issue #167) ─────────────────────


async def test_rewritten_query_flows_to_preprocess_and_retrieve(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    """The crux of the history-aware-retriever pattern: retrieval (and the
    preprocess that feeds it) must run on the REWRITTEN standalone query, not the
    raw follow-up.

    The follow-up "what about them?" names no union, so the only way retrieval
    receives a Boilermakers filter is if ``preprocess`` ran on the condensed
    "Boilermaker foreman wage rate" — proving the rewrite reached BOTH stages.
    """
    chunk = make_chunk(union_name="Boilermakers", text="Boilermaker foreman rate clause.")
    mock_retrieve = AsyncMock(return_value=[chunk])

    with patch(
        "src.routes.query.condense_query",
        new=AsyncMock(return_value="Boilermaker foreman wage rate"),
    ), patch(
        "src.routes.query._get_known_unions",
        new=AsyncMock(return_value=["IBEW", "Boilermakers"]),
    ), patch("src.routes.query.retrieve", new=mock_retrieve), patch(
        "src.routes.query._get_title_map", new=AsyncMock(return_value={})
    ), patch(
        "src.routes.query.generate", new=AsyncMock(return_value=make_generator_result())
    ), patch(
        "src.routes.query._write_query_log", new=AsyncMock(return_value=None)
    ):
        await query_handler(
            QueryRequest.model_validate(
                {
                    "query": "what about them?",
                    "history": [
                        {"role": "user", "content": "What is the foreman rate for all unions?"},
                        {"role": "assistant", "content": "Rates vary by union..."},
                    ],
                }
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    # Retrieval embedded the rewritten standalone query, not the raw follow-up.
    assert mock_retrieve.call_args.args[0] == "Boilermaker foreman wage rate"
    # preprocess consumed the rewrite too: the union filter derives from
    # "Boilermaker", a token absent from the raw "what about them?".
    assert mock_retrieve.call_args.kwargs["union_filters"] == ["Boilermakers"]


async def test_condense_invoked_with_original_query_and_history(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    mock_condense = AsyncMock(return_value="standalone query")

    with patch("src.routes.query.condense_query", new=mock_condense), patch(
        "src.routes.query._get_known_unions", new=AsyncMock(return_value=["IBEW"])
    ), patch(
        "src.routes.query.retrieve", new=AsyncMock(return_value=[make_chunk()])
    ), patch(
        "src.routes.query._get_title_map", new=AsyncMock(return_value={})
    ), patch(
        "src.routes.query.generate", new=AsyncMock(return_value=make_generator_result())
    ), patch(
        "src.routes.query._write_query_log", new=AsyncMock(return_value=None)
    ):
        await query_handler(
            QueryRequest.model_validate(
                {
                    "query": "follow up",
                    "history": [
                        {"role": "user", "content": "prior q"},
                        {"role": "assistant", "content": "prior a"},
                    ],
                }
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert mock_condense.call_args.args[0] == "follow up"
    assert [t.content for t in mock_condense.call_args.args[1]] == ["prior q", "prior a"]


async def test_generator_receives_original_query_and_history(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    mock_generate = AsyncMock(return_value=make_generator_result())

    with patch(
        "src.routes.query.condense_query",
        new=AsyncMock(return_value="Boilermaker foreman wage rate"),
    ), patch(
        "src.routes.query._get_known_unions", new=AsyncMock(return_value=["Boilermakers"])
    ), patch(
        "src.routes.query.retrieve",
        new=AsyncMock(return_value=[make_chunk(union_name="Boilermakers")]),
    ), patch(
        "src.routes.query._get_title_map", new=AsyncMock(return_value={})
    ), patch("src.routes.query.generate", new=mock_generate), patch(
        "src.routes.query._write_query_log", new=AsyncMock(return_value=None)
    ):
        await query_handler(
            QueryRequest.model_validate(
                {
                    "query": "what about them?",
                    "history": [
                        {"role": "user", "content": "What is the foreman rate for all unions?"},
                        {"role": "assistant", "content": "Rates vary by union..."},
                    ],
                }
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    # The generator reads the ORIGINAL follow-up (natural phrasing)...
    assert mock_generate.call_args.args[0] == "what about them?"
    # ...plus the prior turns as conversational history.
    passed_history = mock_generate.call_args.kwargs["history"]
    assert [t.role for t in passed_history] == ["user", "assistant"]
    assert passed_history[0].content == "What is the foreman rate for all unions?"


async def test_query_log_records_original_query_not_rewrite(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    mock_log = AsyncMock(return_value=None)

    with patch(
        "src.routes.query.condense_query", new=AsyncMock(return_value="REWRITTEN STANDALONE")
    ), patch(
        "src.routes.query._get_known_unions", new=AsyncMock(return_value=["IBEW"])
    ), patch(
        "src.routes.query.retrieve", new=AsyncMock(return_value=[make_chunk()])
    ), patch(
        "src.routes.query._get_title_map", new=AsyncMock(return_value={})
    ), patch(
        "src.routes.query.generate", new=AsyncMock(return_value=make_generator_result())
    ), patch("src.routes.query._write_query_log", new=mock_log):
        await query_handler(
            QueryRequest.model_validate(
                {
                    "query": "raw follow up",
                    "history": [
                        {"role": "user", "content": "prior q"},
                        {"role": "assistant", "content": "prior a"},
                    ],
                }
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert mock_log.call_args.kwargs["query_text"] == "raw follow up"


async def test_disclaimer_present_with_history(
    test_settings: Settings, stub_user: CurrentUser
) -> None:
    with _pipeline_patches(
        [make_chunk(union_name="Boilermakers")],
        make_generator_result(answer="Boilermaker foreman rate is $X [SOURCE 1]"),
        known_unions=["Boilermakers"],
        title_map={"doc-001": "Boilermakers 2025-2030 Collective Agreement"},
        condensed="Boilermaker foreman wage rate",
    ):
        response = await query_handler(
            QueryRequest.model_validate(
                {
                    "query": "what about them?",
                    "history": [
                        {"role": "user", "content": "What is the foreman rate for all unions?"},
                        {"role": "assistant", "content": "Rates vary by union..."},
                    ],
                }
            ),
            current_user=stub_user,
            settings=test_settings,
        )

    assert "legal advice" in response.disclaimer
