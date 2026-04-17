"""Tests for services/api/src/rag/retrieval.py.

Covers:
- build_filter: all parameter combinations (pure function, no I/O)
- _point_to_chunk: payload extraction from ScoredPoint
- retrieve: happy path via mocked Ollama + Qdrant
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.models import (
    DatetimeRange,
    FieldCondition,
    Filter,
    MatchValue,
    ScoredPoint,
)

from src.config import Settings
from src.rag.retrieval import (
    COLLECTION,
    TOP_K,
    ChunkResult,
    _point_to_chunk,
    build_filter,
    retrieve,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="test-jwt-secret",  # noqa: S106
    )


def make_scored_point(payload: dict[str, Any]) -> ScoredPoint:
    """Return a minimal ScoredPoint with the given payload."""
    return ScoredPoint(
        id=str(uuid.uuid4()),
        version=0,
        score=0.9,
        payload=payload,
        vector=None,
    )


# ─── build_filter ─────────────────────────────────────────────────────────────


class TestBuildFilter:
    """build_filter is a pure function — no mocking required."""

    def _must_conditions(self, f: Filter) -> list[Any]:
        return f.must or []

    def _expiry_guard(self, f: Filter) -> Filter:
        """The first must condition is always the expiry guard."""
        return self._must_conditions(f)[0]  # type: ignore[return-value]

    # --- Return type ---

    def test_returns_filter_instance(self) -> None:
        assert isinstance(build_filter(None, False, None), Filter)

    # --- Expiry guard (always present) ---

    def test_expiry_guard_is_first_must_condition(self) -> None:
        f = build_filter(None, True, None)
        guard = self._expiry_guard(f)
        assert isinstance(guard, Filter)

    def test_expiry_guard_has_two_should_conditions(self) -> None:
        f = build_filter(None, True, None)
        guard = self._expiry_guard(f)
        assert len(guard.should) == 2  # type: ignore[arg-type]

    def test_expiry_guard_first_should_is_is_null(self) -> None:
        f = build_filter(None, True, None)
        guard = self._expiry_guard(f)
        null_cond: FieldCondition = guard.should[0]  # type: ignore[index]
        assert isinstance(null_cond, FieldCondition)
        assert null_cond.key == "expiry_date"
        assert null_cond.is_null is True

    def test_expiry_guard_second_should_is_datetime_range(self) -> None:
        before = datetime.now(UTC)
        f = build_filter(None, True, None)
        after = datetime.now(UTC)
        guard = self._expiry_guard(f)
        range_cond: FieldCondition = guard.should[1]  # type: ignore[index]
        assert isinstance(range_cond, FieldCondition)
        assert range_cond.key == "expiry_date"
        assert isinstance(range_cond.range, DatetimeRange)
        # gte should be between the timestamps bracketing the call
        assert before <= range_cond.range.gte <= after  # type: ignore[operator]

    # --- include_nuclear_pa = False (default) adds document_type condition ---

    def test_no_nuclear_pa_adds_primary_ca_condition(self) -> None:
        f = build_filter(None, False, None)
        must = self._must_conditions(f)
        # must = [expiry_guard, FieldCondition(document_type=primary_ca)]
        assert len(must) == 2
        doc_type_cond: FieldCondition = must[1]  # type: ignore[assignment]
        assert isinstance(doc_type_cond, FieldCondition)
        assert doc_type_cond.key == "document_type"
        assert isinstance(doc_type_cond.match, MatchValue)
        assert doc_type_cond.match.value == "primary_ca"

    def test_include_nuclear_pa_omits_document_type_condition(self) -> None:
        f = build_filter(None, True, None)
        must = self._must_conditions(f)
        # must = [expiry_guard] only
        assert len(must) == 1

    # --- union_filter ---

    def test_union_filter_adds_union_name_condition(self) -> None:
        f = build_filter("IBEW", True, None)
        must = self._must_conditions(f)
        # must = [expiry_guard, FieldCondition(union_name=IBEW)]
        assert len(must) == 2
        union_cond: FieldCondition = must[1]  # type: ignore[assignment]
        assert isinstance(union_cond, FieldCondition)
        assert union_cond.key == "union_name"
        assert isinstance(union_cond.match, MatchValue)
        assert union_cond.match.value == "IBEW"

    def test_no_union_filter_omits_union_name_condition(self) -> None:
        f = build_filter(None, True, None)
        must = self._must_conditions(f)
        union_conds = [
            c
            for c in must
            if isinstance(c, FieldCondition) and c.key == "union_name"
        ]
        assert len(union_conds) == 0

    # --- agreement_scope ---

    def test_agreement_scope_adds_scope_condition(self) -> None:
        f = build_filter(None, True, "generation")
        must = self._must_conditions(f)
        # must = [expiry_guard, FieldCondition(agreement_scope=generation)]
        assert len(must) == 2
        scope_cond: FieldCondition = must[1]  # type: ignore[assignment]
        assert isinstance(scope_cond, FieldCondition)
        assert scope_cond.key == "agreement_scope"
        assert isinstance(scope_cond.match, MatchValue)
        assert scope_cond.match.value == "generation"

    def test_no_agreement_scope_omits_scope_condition(self) -> None:
        f = build_filter(None, True, None)
        must = self._must_conditions(f)
        scope_conds = [
            c
            for c in must
            if isinstance(c, FieldCondition) and c.key == "agreement_scope"
        ]
        assert len(scope_conds) == 0

    # --- combined ---

    def test_all_params_set_produces_four_must_conditions(self) -> None:
        f = build_filter("Sheet Metal Workers", False, "transmission")
        must = self._must_conditions(f)
        # expiry_guard + union_name + document_type + agreement_scope = 4
        assert len(must) == 4

    def test_transmission_scope_stored_correctly(self) -> None:
        f = build_filter(None, True, "transmission")
        must = self._must_conditions(f)
        scope_cond = next(
            c for c in must if isinstance(c, FieldCondition) and c.key == "agreement_scope"
        )
        assert scope_cond.match.value == "transmission"  # type: ignore[union-attr]


# ─── _point_to_chunk ──────────────────────────────────────────────────────────


class TestPointToChunk:
    def _full_payload(self) -> dict[str, Any]:
        return {
            "document_id": "abc-123",
            "source_filename": "IBEW Generation- 2025-2030 Collective Agreement.pdf",
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "agreement_scope": "generation",
            "effective_date": "2025-05-01",
            "expiry_date": "2030-04-30",
            "article_number": "Article 12",
            "article_title": "Overtime",
            "section_number": "12.03",
            "page_number": 34,
            "is_table": False,
            "text": "Overtime shall be paid at time and one-half.",
        }

    def test_maps_all_fields(self) -> None:
        payload = self._full_payload()
        point = make_scored_point(payload)
        chunk = _point_to_chunk(point)

        assert chunk.document_id == "abc-123"
        assert chunk.source_filename == "IBEW Generation- 2025-2030 Collective Agreement.pdf"
        assert chunk.union_name == "IBEW"
        assert chunk.document_type == "primary_ca"
        assert chunk.agreement_scope == "generation"
        assert chunk.effective_date == "2025-05-01"
        assert chunk.expiry_date == "2030-04-30"
        assert chunk.article_number == "Article 12"
        assert chunk.article_title == "Overtime"
        assert chunk.section_number == "12.03"
        assert chunk.page_number == 34
        assert chunk.is_table is False
        assert chunk.text == "Overtime shall be paid at time and one-half."

    def test_score_and_point_id_captured(self) -> None:
        point = make_scored_point(self._full_payload())
        chunk = _point_to_chunk(point)
        assert chunk.score == 0.9
        assert chunk.point_id == str(point.id)

    def test_optional_fields_default_to_none(self) -> None:
        payload: dict[str, Any] = {
            "document_id": "xyz",
            "source_filename": "doc.pdf",
            "union_name": "UA",
            "document_type": "primary_ca",
            "text": "some text",
        }
        chunk = _point_to_chunk(make_scored_point(payload))
        assert chunk.agreement_scope is None
        assert chunk.effective_date is None
        assert chunk.expiry_date is None
        assert chunk.article_number is None
        assert chunk.article_title is None
        assert chunk.section_number is None
        assert chunk.page_number is None

    def test_is_table_defaults_to_false_when_absent(self) -> None:
        payload: dict[str, Any] = {
            "document_id": "xyz",
            "source_filename": "doc.pdf",
            "union_name": "UA",
            "document_type": "wage_schedule",
            "text": "wage table",
        }
        chunk = _point_to_chunk(make_scored_point(payload))
        assert chunk.is_table is False

    def test_is_table_true_when_set(self) -> None:
        payload: dict[str, Any] = {
            "document_id": "xyz",
            "source_filename": "doc.pdf",
            "union_name": "UA",
            "document_type": "wage_schedule",
            "text": "wage table",
            "is_table": True,
        }
        chunk = _point_to_chunk(make_scored_point(payload))
        assert chunk.is_table is True

    def test_empty_payload_uses_defaults(self) -> None:
        chunk = _point_to_chunk(make_scored_point({}))
        assert chunk.document_id == ""
        assert chunk.source_filename == ""
        assert chunk.union_name == ""
        assert chunk.text == ""

    def test_returns_chunk_result_instance(self) -> None:
        chunk = _point_to_chunk(make_scored_point(self._full_payload()))
        assert isinstance(chunk, ChunkResult)


# ─── retrieve ─────────────────────────────────────────────────────────────────


FAKE_VECTOR: list[float] = [0.1] * 768


def _make_ollama_mock(mock_http: MagicMock) -> AsyncMock:
    """Wire up the httpx.AsyncClient context manager to return a sync-style response.

    httpx's Response.json() and raise_for_status() are synchronous, so the
    mock response must be a regular MagicMock (not AsyncMock) to avoid the
    ``'coroutine' object is not subscriptable`` error.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": FAKE_VECTOR}
    mock_post = AsyncMock(return_value=mock_response)
    mock_http.return_value.__aenter__.return_value.post = mock_post
    return mock_post


class TestRetrieve:
    """retrieve calls Ollama (embed) then Qdrant (search); both are mocked."""

    def _make_hit(self, union: str = "IBEW") -> MagicMock:
        hit = MagicMock(spec=ScoredPoint)
        hit.id = str(uuid.uuid4())
        hit.score = 0.85
        hit.payload = {
            "document_id": str(uuid.uuid4()),
            "source_filename": f"{union} CA.pdf",
            "union_name": union,
            "document_type": "primary_ca",
            "agreement_scope": None,
            "effective_date": "2025-05-01",
            "expiry_date": "2030-04-30",
            "article_number": None,
            "article_title": None,
            "section_number": None,
            "page_number": None,
            "is_table": False,
            "text": f"{union} clause text.",
        }
        return hit

    @pytest.mark.asyncio
    async def test_returns_list_of_chunk_results(self, settings: Settings) -> None:
        hits = [self._make_hit("IBEW"), self._make_hit("Sheet Metal Workers")]

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=hits)
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve("overtime rates", settings=settings)

        assert len(results) == 2
        assert all(isinstance(r, ChunkResult) for r in results)

    @pytest.mark.asyncio
    async def test_calls_ollama_with_correct_params(self, settings: Settings) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            mock_post = _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[])
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates for IBEW", settings=settings)

        mock_post.assert_called_once_with(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": "overtime rates for IBEW"},
            timeout=30.0,
        )

    @pytest.mark.asyncio
    async def test_calls_qdrant_with_correct_collection(self, settings: Settings) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[])
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates", settings=settings)

        call_kwargs = mock_qdrant.search.call_args
        assert call_kwargs.kwargs["collection_name"] == COLLECTION
        assert call_kwargs.kwargs["limit"] == TOP_K
        assert call_kwargs.kwargs["with_payload"] is True

    @pytest.mark.asyncio
    async def test_passes_query_vector_to_qdrant(self, settings: Settings) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[])
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates", settings=settings)

        call_kwargs = mock_qdrant.search.call_args
        assert call_kwargs.kwargs["query_vector"] == FAKE_VECTOR

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_hits(self, settings: Settings) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[])
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve("something obscure", settings=settings)

        assert results == []

    @pytest.mark.asyncio
    async def test_qdrant_initialised_with_settings_url(self, settings: Settings) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[])
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates", settings=settings)

        mock_qdrant_cls.assert_called_once_with(url=settings.qdrant_url)
