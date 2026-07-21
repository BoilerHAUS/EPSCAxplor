"""Tests for services/api/src/rag/retrieval.py.

Covers:
- build_filter: all parameter combinations (pure function, no I/O)
- _point_to_chunk: payload extraction from ScoredPoint
- retrieve: happy path via mocked Ollama + Qdrant
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.http.models import QueryResponse
from qdrant_client.models import (
    DatetimeRange,
    FieldCondition,
    Filter,
    MatchValue,
    ScoredPoint,
)

from src.config import Settings
from src.rag.retrieval import (
    _MIN_PRIMARY_SLOTS,
    _NUCLEAR_PA_PER_UNION,
    _NUCLEAR_PA_SLOTS,
    _PROVISION_MAX_TERMS,
    COLLECTION,
    TOP_K,
    ChunkResult,
    _chunk_classification,
    _merge_union_results,
    _merge_with_priority,
    _point_to_chunk,
    _reserve_baseline_slots,
    _select_current_rate_row,
    _wage_rank_boost,
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

    def _effective_guard(self, f: Filter) -> Filter:
        """The second must condition is always the effective-date guard."""
        return self._must_conditions(f)[1]  # type: ignore[return-value]

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

    # --- effective-date guard (always second must condition) ---

    def test_effective_guard_is_second_must_condition(self) -> None:
        f = build_filter(None, True, None)
        guard = self._effective_guard(f)
        assert isinstance(guard, Filter)
        assert len(guard.should) == 3  # null + lte_now + wage_schedule bypass

    def test_effective_guard_third_should_bypasses_wage_schedule(self) -> None:
        f = build_filter(None, True, None)
        guard = self._effective_guard(f)
        bypass_cond: FieldCondition = guard.should[2]  # type: ignore[index]
        assert isinstance(bypass_cond, FieldCondition)
        assert bypass_cond.key == "document_type"
        assert isinstance(bypass_cond.match, MatchValue)
        assert bypass_cond.match.value == "wage_schedule"

    def test_effective_guard_first_should_is_is_null(self) -> None:
        f = build_filter(None, True, None)
        guard = self._effective_guard(f)
        null_cond: FieldCondition = guard.should[0]  # type: ignore[index]
        assert isinstance(null_cond, FieldCondition)
        assert null_cond.key == "effective_date"
        assert null_cond.is_null is True

    def test_effective_guard_second_should_is_lte_now(self) -> None:
        before = datetime.now(UTC)
        f = build_filter(None, True, None)
        after = datetime.now(UTC)
        guard = self._effective_guard(f)
        range_cond: FieldCondition = guard.should[1]  # type: ignore[index]
        assert isinstance(range_cond, FieldCondition)
        assert range_cond.key == "effective_date"
        assert isinstance(range_cond.range, DatetimeRange)
        assert before <= range_cond.range.lte <= after  # type: ignore[operator]

    # --- include_nuclear_pa = False (default) adds document_type condition ---

    def test_no_nuclear_pa_excludes_nuclear_pa_via_must_not(self) -> None:
        f = build_filter(None, False, None)
        must = self._must_conditions(f)
        # must = [expiry_guard, effective_guard] — NPA exclusion in must_not
        assert len(must) == 2
        must_not = f.must_not or []
        assert len(must_not) == 1
        doc_type_cond: FieldCondition = must_not[0]  # type: ignore[assignment]
        assert isinstance(doc_type_cond, FieldCondition)
        assert doc_type_cond.key == "document_type"
        assert isinstance(doc_type_cond.match, MatchValue)
        assert doc_type_cond.match.value == "nuclear_pa"

    def test_include_nuclear_pa_omits_document_type_condition(self) -> None:
        f = build_filter(None, True, None)
        must = self._must_conditions(f)
        # must = [expiry_guard, effective_guard] only
        assert len(must) == 2

    # --- union_filter ---

    def test_union_filter_adds_union_name_condition(self) -> None:
        f = build_filter("IBEW", True, None)
        must = self._must_conditions(f)
        # must = [expiry_guard, effective_guard, FieldCondition(union_name=IBEW)]
        assert len(must) == 3
        union_cond: FieldCondition = must[2]  # type: ignore[assignment]
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

    def test_agreement_scope_adds_null_tolerant_guard(self) -> None:
        f = build_filter(None, True, "generation")
        must = self._must_conditions(f)
        # must = [expiry_guard, effective_guard, scope_guard]
        assert len(must) == 3
        scope_guard: Filter = must[2]  # type: ignore[assignment]
        assert isinstance(scope_guard, Filter)
        should = scope_guard.should or []
        assert len(should) == 2
        null_cond, match_cond = should
        assert isinstance(null_cond, FieldCondition)
        assert null_cond.key == "agreement_scope"
        assert null_cond.is_null is True
        assert isinstance(match_cond, FieldCondition)
        assert match_cond.key == "agreement_scope"
        assert isinstance(match_cond.match, MatchValue)
        assert match_cond.match.value == "generation"

    def test_no_agreement_scope_omits_scope_condition(self) -> None:
        f = build_filter(None, True, None)
        must = self._must_conditions(f)
        # only the two date guards remain
        assert len(must) == 2

    # --- combined ---

    def test_all_params_set_produces_four_must_one_must_not(self) -> None:
        f = build_filter("Sheet Metal Workers", False, "transmission")
        must = self._must_conditions(f)
        # expiry_guard + effective_guard + union_name + agreement_scope = 4 (nuclear_pa in must_not)
        assert len(must) == 4
        must_not = f.must_not or []
        assert len(must_not) == 1

    def test_transmission_scope_stored_correctly(self) -> None:
        f = build_filter(None, True, "transmission")
        scope_guard: Filter = self._must_conditions(f)[2]  # type: ignore[assignment]
        match_cond = scope_guard.should[1]  # type: ignore[index]
        assert match_cond.match.value == "transmission"  # type: ignore[union-attr]


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


def _make_query_response(hits: list[ScoredPoint]) -> QueryResponse:
    return QueryResponse(points=hits)


def _union_filter_value(filt: Filter) -> str | None:
    for condition in filt.must or []:
        if isinstance(condition, FieldCondition) and condition.key == "union_name":
            return str(condition.match.value)  # type: ignore[union-attr]
    return None


class TestMergeUnionResults:
    def test_interleaves_union_results_round_robin(self) -> None:
        ibew_results = [
            ChunkResult(
                point_id="ibew-1",
                score=0.95,
                document_id="doc-1",
                source_filename="ibew-1.pdf",
                union_name="IBEW",
                document_type="primary_ca",
                agreement_scope=None,
                effective_date=None,
                expiry_date=None,
                article_number=None,
                article_title=None,
                section_number=None,
                page_number=None,
                is_table=False,
                text="IBEW first",
            ),
            ChunkResult(
                point_id="ibew-2",
                score=0.9,
                document_id="doc-2",
                source_filename="ibew-2.pdf",
                union_name="IBEW",
                document_type="primary_ca",
                agreement_scope=None,
                effective_date=None,
                expiry_date=None,
                article_number=None,
                article_title=None,
                section_number=None,
                page_number=None,
                is_table=False,
                text="IBEW second",
            ),
        ]
        sheet_metal_results = [
            ChunkResult(
                point_id="sm-1",
                score=0.93,
                document_id="doc-3",
                source_filename="sm-1.pdf",
                union_name="Sheet Metal Workers",
                document_type="primary_ca",
                agreement_scope=None,
                effective_date=None,
                expiry_date=None,
                article_number=None,
                article_title=None,
                section_number=None,
                page_number=None,
                is_table=False,
                text="Sheet Metal first",
            )
        ]

        merged = _merge_union_results([ibew_results, sheet_metal_results], limit=3)

        assert [chunk.point_id for chunk in merged] == ["ibew-1", "sm-1", "ibew-2"]

    def test_dedupes_duplicate_point_ids(self) -> None:
        duplicate = ChunkResult(
            point_id="dup-1",
            score=0.95,
            document_id="doc-1",
            source_filename="dup.pdf",
            union_name="IBEW",
            document_type="primary_ca",
            agreement_scope=None,
            effective_date=None,
            expiry_date=None,
            article_number=None,
            article_title=None,
            section_number=None,
            page_number=None,
            is_table=False,
            text="duplicate",
        )

        merged = _merge_union_results([[duplicate], [duplicate]], limit=5)

        assert [chunk.point_id for chunk in merged] == ["dup-1"]


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
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response(hits))
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
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates for IBEW", settings=settings)

        mock_post.assert_called_once_with(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": "search_query: overtime rates for IBEW"},
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
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates", settings=settings)

        call_kwargs = mock_qdrant.query_points.call_args
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
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates", settings=settings)

        call_kwargs = mock_qdrant.query_points.call_args
        assert call_kwargs.kwargs["query"] == FAKE_VECTOR

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_hits(self, settings: Settings) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
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
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates", settings=settings)

        # Unset key (fixture default) → the reader is built keyless (api_key=None),
        # preserving local/dev behavior (#144).
        mock_qdrant_cls.assert_called_once_with(
            url=settings.qdrant_url, api_key=settings.qdrant_api_key
        )
        assert settings.qdrant_api_key is None

    @pytest.mark.asyncio
    async def test_qdrant_initialised_with_api_key_when_configured(self) -> None:
        # When QDRANT_API_KEY is set, the reader must forward it so it is not
        # locked out once Qdrant enforces auth (#144).
        settings = Settings(
            database_url="postgresql://user:pass@localhost/epsca",
            qdrant_url="http://localhost:6333",
            ollama_url="http://localhost:11434",
            anthropic_api_key="test-key",
            jwt_secret="test-jwt-secret",  # noqa: S106
            qdrant_api_key="reader-secret",  # noqa: S106
        )
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve("overtime rates", settings=settings)

        mock_qdrant_cls.assert_called_once_with(
            url="http://localhost:6333", api_key="reader-secret"
        )

    @pytest.mark.asyncio
    async def test_single_union_filter_still_uses_one_qdrant_query(
        self, settings: Settings
    ) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "IBEW overtime rates",
                union_filters=["IBEW"],
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 1
        query_filter = mock_qdrant.query_points.await_args.kwargs["query_filter"]
        assert _union_filter_value(query_filter) == "IBEW"

    @pytest.mark.asyncio
    async def test_multi_union_queries_fan_out_and_merge_results(
        self, settings: Settings
    ) -> None:
        ibew_hits = [self._make_hit("IBEW"), self._make_hit("IBEW")]
        sheet_metal_hits = [self._make_hit("Sheet Metal Workers")]

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response(ibew_hits),
                    _make_query_response(sheet_metal_hits),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Compare IBEW and Sheet Metal overtime rules",
                union_filters=["IBEW", "Sheet Metal Workers"],
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 2
        first_filter = mock_qdrant.query_points.await_args_list[0].kwargs["query_filter"]
        second_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        assert _union_filter_value(first_filter) == "IBEW"
        assert _union_filter_value(second_filter) == "Sheet Metal Workers"
        assert [chunk.union_name for chunk in results] == [
            "IBEW",
            "Sheet Metal Workers",
            "IBEW",
        ]


def _make_chunk(point_id: str, document_type: str = "primary_ca") -> ChunkResult:
    return ChunkResult(
        point_id=point_id,
        score=0.9,
        document_id="doc-1",
        source_filename="test.pdf",
        union_name="IBEW",
        document_type=document_type,
        agreement_scope=None,
        effective_date=None,
        expiry_date=None,
        article_number=None,
        article_title=None,
        section_number=None,
        page_number=None,
        is_table=document_type == "wage_schedule",
        text="text",
    )


class TestMergeWithPriority:
    def test_leading_chunks_lead_in_output(self) -> None:
        primary = [_make_chunk("ca-1"), _make_chunk("ca-2")]
        leading = [_make_chunk("ws-1", "wage_schedule"), _make_chunk("ws-2", "wage_schedule")]
        result = _merge_with_priority(primary, leading)
        assert result[0].point_id == "ws-1"
        assert result[1].point_id == "ws-2"

    def test_primary_chunks_fill_remaining_slots(self) -> None:
        primary = [_make_chunk("ca-1"), _make_chunk("ca-2")]
        leading = [_make_chunk("ws-1", "wage_schedule")]
        result = _merge_with_priority(primary, leading)
        assert result[1].point_id == "ca-1"
        assert result[2].point_id == "ca-2"

    def test_deduplicates_by_point_id(self) -> None:
        shared = _make_chunk("shared-1", "wage_schedule")
        primary = [shared, _make_chunk("ca-1")]
        leading = [shared, _make_chunk("ws-1", "wage_schedule")]
        result = _merge_with_priority(primary, leading)
        ids = [c.point_id for c in result]
        assert ids.count("shared-1") == 1

    def test_respects_limit(self) -> None:
        primary = [_make_chunk(f"ca-{i}") for i in range(8)]
        leading = [_make_chunk(f"ws-{i}", "wage_schedule") for i in range(5)]
        result = _merge_with_priority(primary, leading, limit=10)
        assert len(result) == 10

    def test_empty_leading_returns_primary(self) -> None:
        primary = [_make_chunk("ca-1"), _make_chunk("ca-2")]
        result = _merge_with_priority(primary, [])
        assert [c.point_id for c in result] == ["ca-1", "ca-2"]

    def test_empty_primary_returns_leading(self) -> None:
        leading = [_make_chunk("ws-1", "wage_schedule")]
        result = _merge_with_priority([], leading)
        assert result[0].point_id == "ws-1"


class TestWageRankBoost:
    """Deterministic re-ranking of wage chunks by classification/location."""

    def _payload(
        self,
        names: list[str] | None = None,
        city: str = "Hamilton",
        local: str = "Local 105",
    ) -> dict[str, Any]:
        return {
            "classification_names": names or [],
            "city": city,
            "local": local,
        }

    def test_journeyperson_query_boosts_journeyman_chunk(self) -> None:
        query = "what is the journeyperson hourly rate for ibew electricians?"
        boost = _wage_rank_boost(query, self._payload(["JOURNEYMAN", "WELDER"]))
        assert boost == pytest.approx(0.15)

    def test_journeyperson_query_does_not_boost_apprentice_chunk(self) -> None:
        query = "what is the journeyperson hourly rate for ibew electricians?"
        boost = _wage_rank_boost(query, self._payload(["ELECTRICIAN APPRENTICE"]))
        assert boost == 0.0

    def test_foreman_query_boosts_foreman_chunk(self) -> None:
        query = "what is the foreman wage premium?"
        boost = _wage_rank_boost(query, self._payload(["ELECTRICIAN", "FOREMAN"]))
        assert boost == pytest.approx(0.15)

    def test_city_match_adds_location_boost(self) -> None:
        query = "sheet metal journeyperson rate in hamilton"
        boost = _wage_rank_boost(query, self._payload(["JOURNEYMAN AND WELDER"]))
        assert boost == pytest.approx(0.25)

    def test_local_number_match_adds_location_boost(self) -> None:
        query = "apprentice rates for local 105"
        boost = _wage_rank_boost(query, self._payload(["ELECTRICIAN APPRENTICE", "1st Period"]))
        assert boost == pytest.approx(0.25)

    def test_chunk_without_metadata_gets_no_boost(self) -> None:
        query = "journeyperson hourly rate"
        assert _wage_rank_boost(query, {}) == 0.0

    def test_classification_boost_applied_once(self) -> None:
        # A chunk matching two classification aliases still gets one boost.
        query = "journeyperson and welder rates"
        boost = _wage_rank_boost(
            query, self._payload(["JOURNEYMAN AND WELDER"], city="", local="")
        )
        assert boost == pytest.approx(0.15)

    def test_apprentice_label_mentioning_journeyman_not_boosted(self) -> None:
        # UA/SM apprentice labels embed "of Journeyman Rate"; the chunk's
        # primary classification is still apprentice, so a journeyperson
        # query must not boost it.
        query = "which union has the higher journeyperson base rate?"
        boost = _wage_rank_boost(
            query,
            self._payload(
                ["APPRENTICE", "1st Period - 40 % of Journeyman Rate"],
                city="",
                local="",
            ),
        )
        assert boost == 0.0

    def test_journeyman_and_welder_classified_as_journeyman(self) -> None:
        query = "journeyperson hourly rate"
        boost = _wage_rank_boost(
            query, self._payload(["JOURNEYMAN AND WELDER"], city="", local="")
        )
        assert boost == pytest.approx(0.15)

    def test_chunk_classification_priority(self) -> None:
        assert (
            _chunk_classification(
                {"classification_names": ["APPRENTICE", "3rd Period - 60% of Journeyman Rate"]}
            )
            == "apprentice"
        )
        assert (
            _chunk_classification({"classification_names": ["SUBFOREMAN"]})
            == "subforeman"
        )
        assert (
            _chunk_classification({"classification_names": ["ELECTRICIAN", "FOREMAN"]})
            == "foreman"
        )
        assert _chunk_classification({"classification_names": []}) is None


class TestReserveBaselineSlots:
    """Premium queries must include journeyperson baseline chunks."""

    def _hit(self, point_id: str, names: list[str], local: str, score: float) -> Any:
        hit = MagicMock(spec=ScoredPoint)
        hit.id = point_id
        hit.score = score
        hit.payload = {
            "classification_names": names,
            "local": local,
            "city": local.split()[-1],
        }
        return hit

    def test_baseline_replaces_tail_and_prefers_same_local(self) -> None:
        foremen = [
            self._hit(f"f{i}", ["FOREMAN"], f"Local {i}", 0.80 - i * 0.01)
            for i in range(5)
        ]
        same_local_journeyman = self._hit("j-same", ["JOURNEYMAN"], "Local 0", 0.60)
        other_journeyman = self._hit("j-other", ["JOURNEYMAN"], "Local 99", 0.70)
        ranked = [*foremen, other_journeyman, same_local_journeyman]

        result = _reserve_baseline_slots(ranked, foremen[:5], limit=5)

        ids = [hit.id for hit in result]
        assert len(ids) == 5
        # Same-local baseline outranks the higher-scoring other-local one.
        assert ids[3] == "j-same"
        assert ids[4] == "j-other"

    def test_no_change_when_baseline_already_selected(self) -> None:
        selected = [
            self._hit("f1", ["FOREMAN"], "Local 1", 0.8),
            self._hit("j1", ["JOURNEYMAN"], "Local 1", 0.7),
        ]
        assert _reserve_baseline_slots(selected, selected, limit=5) == selected

    def test_no_change_when_no_baseline_exists(self) -> None:
        selected = [self._hit("f1", ["FOREMAN"], "Local 1", 0.8)]
        assert _reserve_baseline_slots(selected, selected, limit=5) == selected


class TestRetrieveWageQuery:
    def _make_hit(self, point_id: str, document_type: str = "primary_ca") -> ScoredPoint:
        hit = MagicMock(spec=ScoredPoint)
        hit.id = point_id
        hit.score = 0.85
        hit.payload = {
            "document_id": str(uuid.uuid4()),
            "source_filename": "test.pdf",
            "union_name": "IBEW",
            "document_type": document_type,
            "agreement_scope": None,
            "effective_date": "2025-05-01",
            "expiry_date": None,
            "article_number": None,
            "article_title": None,
            "section_number": None,
            "page_number": None,
            "is_table": document_type == "wage_schedule",
            "text": "text",
        }
        return hit

    @pytest.mark.asyncio
    async def test_wage_query_triggers_second_qdrant_call(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        wage_hit = self._make_hit("ws-1", "wage_schedule")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([wage_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "journeyperson hourly rate for IBEW",
                union_filters=["IBEW"],
                is_wage_query=True,
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 2
        assert results[0].point_id == "ws-1"
        assert results[1].point_id == "ca-1"

    @pytest.mark.asyncio
    async def test_cross_union_wage_query_fans_out_per_union(
        self, settings: Settings
    ) -> None:
        """Multi-union rate queries run one wage pass per union so both
        unions' wage chunks appear, instead of one unfiltered pass."""
        ibew_ca = self._make_hit("ibew-ca")
        ua_ca = self._make_hit("ua-ca")
        ibew_wage = self._make_hit("ibew-ws", "wage_schedule")
        ua_wage = self._make_hit("ua-ws", "wage_schedule")
        ua_wage.payload["union_name"] = "United Association"

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ibew_ca]),   # primary IBEW
                    _make_query_response([ua_ca]),     # primary UA
                    _make_query_response([ibew_wage]),  # wage IBEW
                    _make_query_response([ua_wage]),    # wage UA
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Which union has the higher journeyperson base rate?",
                union_filters=["IBEW", "United Association"],
                is_wage_query=True,
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 4
        wage_calls = mock_qdrant.query_points.await_args_list[2:]
        wage_unions = [
            _union_filter_value(call.kwargs["query_filter"]) for call in wage_calls
        ]
        assert wage_unions == ["IBEW", "United Association"]
        # Wage chunks from both unions lead the merged results.
        assert [c.point_id for c in results[:2]] == ["ibew-ws", "ua-ws"]

    @pytest.mark.asyncio
    async def test_wage_pass_applies_null_tolerant_scope_filter(
        self, settings: Settings
    ) -> None:
        """'generation project' rate queries must not surface the same
        local's TRANSMISSION wage schedule in the wage slots (W15)."""
        ca_hit = self._make_hit("ca-1")
        wage_hit = self._make_hit("ws-1", "wage_schedule")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([wage_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "Labourers foreman rate on a generation project in Sarnia",
                union_filters=["Labourers"],
                agreement_scope="generation",
                is_wage_query=True,
                settings=settings,
            )

        wage_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        scope_guards = [
            c for c in wage_filter.must
            if isinstance(c, Filter)
            and any(
                isinstance(s, FieldCondition) and s.key == "agreement_scope"
                for s in (c.should or [])
            )
        ]
        assert len(scope_guards) == 1
        should = scope_guards[0].should
        assert should[0].is_null is True
        assert should[1].match.value == "generation"

    @pytest.mark.asyncio
    async def test_non_wage_query_uses_single_qdrant_call(
        self, settings: Settings
    ) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "What are the layoff notice requirements?",
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 1


def _doc_type_values(filt: Filter) -> list[str]:
    """Return the values of every top-level document_type FieldCondition in must."""
    return [
        str(c.match.value)  # type: ignore[union-attr]
        for c in filt.must or []
        if isinstance(c, FieldCondition) and c.key == "document_type"
    ]


def _scope_guard(filt: Filter) -> Filter | None:
    """Return the null-tolerant agreement_scope guard sub-filter, if present."""
    for c in filt.must or []:
        if isinstance(c, Filter) and any(
            isinstance(s, FieldCondition) and s.key == "agreement_scope"
            for s in (c.should or [])
        ):
            return c
    return None


def _has_date_guard(filt: Filter, key: str) -> bool:
    """True if *filt*'s must contains a should-guard over the given date key."""
    return any(
        isinstance(c, Filter)
        and any(
            isinstance(s, FieldCondition) and s.key == key for s in (c.should or [])
        )
        for c in filt.must or []
    )


class TestRetrieveNuclearQuery:
    """include_nuclear_pa runs a dedicated NPA pass so NPA chunks are
    guaranteed representation alongside the primary CA (issue #115)."""

    def _make_hit(
        self,
        point_id: str,
        document_type: str = "primary_ca",
        union: str = "IBEW",
    ) -> ScoredPoint:
        hit = MagicMock(spec=ScoredPoint)
        hit.id = point_id
        hit.score = 0.85
        hit.payload = {
            "document_id": str(uuid.uuid4()),
            "source_filename": "test.pdf",
            "union_name": union,
            "document_type": document_type,
            "agreement_scope": None,
            "effective_date": "2025-05-01",
            "expiry_date": None,
            "article_number": None,
            "article_title": None,
            "section_number": None,
            "page_number": None,
            "is_table": False,
            "text": "text",
        }
        return hit

    @pytest.mark.asyncio
    async def test_nuclear_query_triggers_second_qdrant_call(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        npa_hit = self._make_hit("npa-1", "nuclear_pa")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([npa_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "What overtime provisions apply at the Darlington nuclear project?",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                settings=settings,
            )

        # Primary pass + guaranteed NPA pass.
        assert mock_qdrant.query_points.await_count == 2
        # NPA chunk leads so it is guaranteed to appear in context/citations.
        assert results[0].point_id == "npa-1"
        assert results[1].point_id == "ca-1"

    @pytest.mark.asyncio
    async def test_nuclear_pass_filters_to_nuclear_pa_doc_type_and_union(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        npa_hit = self._make_hit("npa-1", "nuclear_pa")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([npa_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "shift premiums for Bruce Power nuclear work",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                settings=settings,
            )

        npa_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        assert _doc_type_values(npa_filter) == ["nuclear_pa"]
        assert _union_filter_value(npa_filter) == "IBEW"

    @pytest.mark.asyncio
    async def test_nuclear_pass_uses_slot_limit(self, settings: Settings) -> None:
        ca_hit = self._make_hit("ca-1")
        npa_hit = self._make_hit("npa-1", "nuclear_pa")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([npa_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "nuclear project agreement premium rates",
                include_nuclear_pa=True,
                settings=settings,
            )

        npa_call = mock_qdrant.query_points.await_args_list[1]
        assert npa_call.kwargs["limit"] == _NUCLEAR_PA_SLOTS

    @pytest.mark.asyncio
    async def test_cross_union_nuclear_query_fans_out_per_union(
        self, settings: Settings
    ) -> None:
        ibew_ca = self._make_hit("ibew-ca", union="IBEW")
        ua_ca = self._make_hit("ua-ca", union="United Association")
        ibew_npa = self._make_hit("ibew-npa", "nuclear_pa", "IBEW")
        ua_npa = self._make_hit("ua-npa", "nuclear_pa", "United Association")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ibew_ca]),   # primary IBEW
                    _make_query_response([ua_ca]),     # primary UA
                    _make_query_response([ibew_npa]),  # nuclear IBEW
                    _make_query_response([ua_npa]),    # nuclear UA
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Compare Darlington provisions for IBEW and United Association",
                union_filters=["IBEW", "United Association"],
                include_nuclear_pa=True,
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 4
        npa_calls = mock_qdrant.query_points.await_args_list[2:]
        npa_unions = [
            _union_filter_value(call.kwargs["query_filter"]) for call in npa_calls
        ]
        assert npa_unions == ["IBEW", "United Association"]
        # NPA chunks from both unions lead the merged results.
        assert [c.point_id for c in results[:2]] == ["ibew-npa", "ua-npa"]

    @pytest.mark.asyncio
    async def test_nuclear_and_wage_query_guarantees_both(
        self, settings: Settings
    ) -> None:
        """A nuclear rate query runs primary + NPA pass + wage pass, and both
        the NPA and wage chunks lead the primary CA content."""
        ca_hit = self._make_hit("ca-1")
        npa_hit = self._make_hit("npa-1", "nuclear_pa")
        wage_hit = self._make_hit("ws-1", "wage_schedule")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),    # primary
                    _make_query_response([npa_hit]),   # nuclear pass
                    _make_query_response([wage_hit]),  # wage pass
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Darlington journeyperson premium rate for IBEW",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                is_wage_query=True,
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 3
        ids = [c.point_id for c in results]
        assert {"npa-1", "ws-1", "ca-1"} <= set(ids)
        # Both guaranteed passes lead the primary CA chunk.
        assert ids.index("npa-1") < ids.index("ca-1")
        assert ids.index("ws-1") < ids.index("ca-1")
        # Nuclear leads wage (deterministic ordering).
        assert ids.index("npa-1") < ids.index("ws-1")

    @pytest.mark.asyncio
    async def test_nuclear_pass_applies_null_tolerant_scope_filter(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        npa_hit = self._make_hit("npa-1", "nuclear_pa")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([npa_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "Darlington generation nuclear premium for IBEW",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                agreement_scope="generation",
                settings=settings,
            )

        npa_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        guard = _scope_guard(npa_filter)
        assert guard is not None
        should = guard.should or []
        assert should[0].is_null is True  # type: ignore[union-attr]
        assert should[1].match.value == "generation"  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_non_nuclear_query_uses_single_qdrant_call(
        self, settings: Settings
    ) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "What are the general holiday provisions?",
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 1

    @pytest.mark.asyncio
    async def test_nuclear_pass_applies_expiry_and_effective_guards(
        self, settings: Settings
    ) -> None:
        """The guaranteed NPA pass must carry the same expiry/effective-date
        guards as the primary pass, or a superseded NPA could be surfaced as
        current."""
        ca_hit = self._make_hit("ca-1")
        npa_hit = self._make_hit("npa-1", "nuclear_pa")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([npa_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "Darlington nuclear premium for IBEW",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                settings=settings,
            )

        npa_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        assert _has_date_guard(npa_filter, "expiry_date")
        assert _has_date_guard(npa_filter, "effective_date")

    @pytest.mark.asyncio
    async def test_primary_ca_survives_crowding_single_union_nuclear_wage(
        self, settings: Settings
    ) -> None:
        """A nuclear rate query fills most leading slots (NPA + wage), but the
        primary CA floor must still survive in the context window."""
        ca_hits = [self._make_hit(f"ca-{i}") for i in range(TOP_K)]
        npa_hits = [
            self._make_hit(f"npa-{i}", "nuclear_pa") for i in range(_NUCLEAR_PA_SLOTS)
        ]
        wage_hits = [self._make_hit(f"ws-{i}", "wage_schedule") for i in range(5)]

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response(ca_hits),    # primary
                    _make_query_response(npa_hits),   # nuclear pass
                    _make_query_response(wage_hits),  # wage pass
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Darlington journeyperson premium rate for IBEW",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                is_wage_query=True,
                settings=settings,
            )

        assert len(results) == TOP_K
        doc_types = [c.document_type for c in results]
        assert doc_types.count("primary_ca") >= _MIN_PRIMARY_SLOTS
        assert "nuclear_pa" in doc_types
        assert "wage_schedule" in doc_types

    @pytest.mark.asyncio
    async def test_primary_ca_survives_crowding_cross_union_nuclear_wage(
        self, settings: Settings
    ) -> None:
        """The worst case: two unions + both flags produce TOP_K leading chunks
        (NPA fan-out + wage fan-out).  Without the primary reserve this yields
        zero CA context; the floor guarantees the base agreements survive."""
        ibew_ca = [self._make_hit(f"ibew-ca-{i}", union="IBEW") for i in range(5)]
        ua_ca = [
            self._make_hit(f"ua-ca-{i}", union="United Association") for i in range(5)
        ]
        ibew_npa = [
            self._make_hit(f"ibew-npa-{i}", "nuclear_pa", "IBEW")
            for i in range(_NUCLEAR_PA_PER_UNION)
        ]
        ua_npa = [
            self._make_hit(f"ua-npa-{i}", "nuclear_pa", "United Association")
            for i in range(_NUCLEAR_PA_PER_UNION)
        ]
        ibew_ws = [
            self._make_hit(f"ibew-ws-{i}", "wage_schedule", "IBEW") for i in range(3)
        ]
        ua_ws = [
            self._make_hit(f"ua-ws-{i}", "wage_schedule", "United Association")
            for i in range(3)
        ]

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response(ibew_ca),   # primary IBEW
                    _make_query_response(ua_ca),     # primary UA
                    _make_query_response(ibew_npa),  # nuclear IBEW
                    _make_query_response(ua_npa),    # nuclear UA
                    _make_query_response(ibew_ws),   # wage IBEW
                    _make_query_response(ua_ws),     # wage UA
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Compare Darlington journeyperson rates for IBEW and United Association",
                union_filters=["IBEW", "United Association"],
                include_nuclear_pa=True,
                is_wage_query=True,
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 6
        assert len(results) == TOP_K
        doc_types = [c.document_type for c in results]
        assert doc_types.count("primary_ca") >= _MIN_PRIMARY_SLOTS
        assert "nuclear_pa" in doc_types
        assert "wage_schedule" in doc_types

    @pytest.mark.asyncio
    async def test_nuclear_query_with_no_npa_docs_degrades_to_primary(
        self, settings: Settings
    ) -> None:
        """A union with no NPA documents: the nuclear pass returns nothing and
        results fall back cleanly to the primary CA (no crash, no empty slot)."""
        ca_hit = self._make_hit("ca-1")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),  # primary
                    _make_query_response([]),        # nuclear pass: no NPA docs
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Labourers nuclear site provisions",
                union_filters=["Labourers"],
                include_nuclear_pa=True,
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 2
        assert [c.point_id for c in results] == ["ca-1"]


def _doc_type_must_not_values(filt: Filter) -> list[str]:
    """Return document_type values excluded via must_not."""
    return [
        str(c.match.value)  # type: ignore[union-attr]
        for c in filt.must_not or []
        if isinstance(c, FieldCondition) and c.key == "document_type"
    ]


class TestRetrieveProvisionRecall:
    """Provision-recall pass: re-embedding focused terms surfaces the definitive
    clause into `leading` for narrative/table recall gaps (issue #78)."""

    def _make_hit(
        self,
        point_id: str,
        document_type: str = "primary_ca",
        union: str = "United Association",
    ) -> ScoredPoint:
        hit = MagicMock(spec=ScoredPoint)
        hit.id = point_id
        hit.score = 0.85
        hit.payload = {
            "document_id": str(uuid.uuid4()),
            "source_filename": "test.pdf",
            "union_name": union,
            "document_type": document_type,
            "agreement_scope": None,
            "effective_date": "2025-05-01",
            "expiry_date": None,
            "article_number": None,
            "article_title": None,
            "section_number": None,
            "page_number": None,
            "is_table": document_type == "wage_schedule",
            "text": "text",
        }
        return hit

    @pytest.mark.asyncio
    async def test_provision_query_triggers_extra_call_and_leads(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        prov_hit = self._make_hit("prov-1")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([prov_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "What is the double-time rate provision for United Association workers?",
                union_filters=["United Association"],
                provision_terms=["double time overtime rate"],
                settings=settings,
            )

        # Primary pass + one provision-term pass.
        assert mock_qdrant.query_points.await_count == 2
        # Provision chunk leads so it is guaranteed a place in context/citations.
        assert results[0].point_id == "prov-1"
        assert results[1].point_id == "ca-1"

    @pytest.mark.asyncio
    async def test_provision_pass_inherits_date_guards(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        prov_hit = self._make_hit("prov-1")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([prov_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "double-time rate provision",
                union_filters=["United Association"],
                provision_terms=["double time overtime rate"],
                settings=settings,
            )

        prov_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        assert _has_date_guard(prov_filter, "expiry_date")
        assert _has_date_guard(prov_filter, "effective_date")
        assert _union_filter_value(prov_filter) == "United Association"

    @pytest.mark.asyncio
    async def test_provision_pass_excludes_npa_when_not_nuclear(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        prov_hit = self._make_hit("prov-1")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([prov_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "foreman wage premium",
                union_filters=["IBEW"],
                include_nuclear_pa=False,
                provision_terms=["foreperson wage differential"],
                settings=settings,
            )

        prov_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        assert "nuclear_pa" in _doc_type_must_not_values(prov_filter)

    @pytest.mark.asyncio
    async def test_provision_pass_allows_npa_when_nuclear(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        npa_prov_hit = self._make_hit("prov-npa-1", "nuclear_pa", "IBEW")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),   # primary
                    _make_query_response([npa_prov_hit]),  # provision term
                    _make_query_response([]),         # nuclear pass (no extra)
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "additional provisions at Darlington",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                provision_terms=["Darlington"],
                settings=settings,
            )

        prov_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        # include_nuclear_pa=True → NPA not excluded, so an NPA-typed provision
        # chunk (the Darlington LOU) is eligible and leads.
        assert "nuclear_pa" not in _doc_type_must_not_values(prov_filter)
        assert results[0].point_id == "prov-npa-1"

    @pytest.mark.asyncio
    async def test_provision_pass_applies_null_tolerant_scope_filter(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        prov_hit = self._make_hit("prov-1")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),
                    _make_query_response([prov_hit]),
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "IBEW generation foreman differential",
                union_filters=["IBEW"],
                agreement_scope="generation",
                provision_terms=["foreperson wage differential"],
                settings=settings,
            )

        prov_filter = mock_qdrant.query_points.await_args_list[1].kwargs["query_filter"]
        guard = _scope_guard(prov_filter)
        assert guard is not None
        should = guard.should or []
        assert should[0].is_null is True  # type: ignore[union-attr]
        assert should[1].match.value == "generation"  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_cross_union_provision_query_fans_out_per_union(
        self, settings: Settings
    ) -> None:
        ibew_ca = self._make_hit("ibew-ca", union="IBEW")
        ua_ca = self._make_hit("ua-ca", union="United Association")
        ibew_prov = self._make_hit("ibew-prov", union="IBEW")
        ua_prov = self._make_hit("ua-prov", union="United Association")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ibew_ca]),   # primary IBEW
                    _make_query_response([ua_ca]),     # primary UA
                    _make_query_response([ibew_prov]),  # provision IBEW
                    _make_query_response([ua_prov]),    # provision UA
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Compare double-time provisions for IBEW and United Association",
                union_filters=["IBEW", "United Association"],
                provision_terms=["double time overtime rate"],
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 4
        prov_calls = mock_qdrant.query_points.await_args_list[2:]
        prov_unions = [
            _union_filter_value(call.kwargs["query_filter"]) for call in prov_calls
        ]
        assert prov_unions == ["IBEW", "United Association"]
        # Provision chunks from both unions lead the merged results.
        assert [c.point_id for c in results[:2]] == ["ibew-prov", "ua-prov"]

    @pytest.mark.asyncio
    async def test_term_cap_bounds_provision_qdrant_calls(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")
        prov_hits = [self._make_hit(f"prov-{i}") for i in range(_PROVISION_MAX_TERMS)]

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[_make_query_response([ca_hit])]
                + [_make_query_response([h]) for h in prov_hits]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            # Supply more terms than the cap; only the first _PROVISION_MAX_TERMS
            # are embedded/searched.
            await retrieve(
                "many provision terms",
                union_filters=["IBEW"],
                provision_terms=[f"term {i}" for i in range(_PROVISION_MAX_TERMS + 2)],
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 1 + _PROVISION_MAX_TERMS

    @pytest.mark.asyncio
    async def test_provision_npa_and_wage_all_lead_and_floor_survives(
        self, settings: Settings
    ) -> None:
        """Worst case: provision + nuclear + wage all fire.  All three lead in
        order (provision → NPA → wage) and the primary-CA floor still holds."""
        ca_hits = [self._make_hit(f"ca-{i}") for i in range(TOP_K)]
        prov_hit = self._make_hit("prov-1")
        npa_hits = [
            self._make_hit(f"npa-{i}", "nuclear_pa") for i in range(_NUCLEAR_PA_SLOTS)
        ]
        wage_hits = [self._make_hit(f"ws-{i}", "wage_schedule") for i in range(5)]

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response(ca_hits),    # primary
                    _make_query_response([prov_hit]),  # provision term
                    _make_query_response(npa_hits),   # nuclear pass
                    _make_query_response(wage_hits),  # wage pass
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Darlington journeyperson double-time premium for IBEW",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                is_wage_query=True,
                provision_terms=["double time overtime rate"],
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 4
        assert len(results) == TOP_K
        doc_types = [c.document_type for c in results]
        assert doc_types.count("primary_ca") >= _MIN_PRIMARY_SLOTS
        assert "nuclear_pa" in doc_types
        assert "wage_schedule" in doc_types
        ids = [c.point_id for c in results]
        # Ordering contract: provision → NPA → wage.
        assert ids.index("prov-1") < ids.index("npa-0")
        assert ids.index("npa-0") < ids.index("ws-0")

    @pytest.mark.asyncio
    async def test_wage_survives_max_provision_and_npa_crowding(
        self, settings: Settings
    ) -> None:
        """Regression lock (review HIGH): with provision + NPA + wage all firing
        at high hit counts, round-robin interleaving keeps the guaranteed wage
        table in the window — plain concatenation would let provision + NPA fill
        every leading slot and drop wage entirely."""
        ca_hits = [self._make_hit(f"ca-{i}") for i in range(TOP_K)]
        # Two provision terms → up to 4 distinct provision hits after merge.
        prov_a = [self._make_hit("prov-0"), self._make_hit("prov-1")]
        prov_b = [self._make_hit("prov-2"), self._make_hit("prov-3")]
        npa_hits = [
            self._make_hit(f"npa-{i}", "nuclear_pa") for i in range(_NUCLEAR_PA_SLOTS)
        ]
        wage_hits = [self._make_hit(f"ws-{i}", "wage_schedule") for i in range(5)]

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response(ca_hits),    # primary
                    _make_query_response(prov_a),     # provision term 1
                    _make_query_response(prov_b),     # provision term 2
                    _make_query_response(npa_hits),   # nuclear pass
                    _make_query_response(wage_hits),  # wage pass
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "Darlington foreman premium double-time rate for IBEW",
                union_filters=["IBEW"],
                include_nuclear_pa=True,
                is_wage_query=True,
                provision_terms=[
                    "foreperson wage differential",
                    "double time overtime rate",
                ],
                settings=settings,
            )

        assert len(results) == TOP_K
        doc_types = [c.document_type for c in results]
        # All three guaranteed passes keep representation; wage is not starved.
        assert "wage_schedule" in doc_types
        assert "nuclear_pa" in doc_types
        assert any(c.point_id.startswith("prov-") for c in results)
        assert doc_types.count("primary_ca") >= _MIN_PRIMARY_SLOTS

    @pytest.mark.asyncio
    async def test_provision_pass_with_no_hits_degrades_to_primary(
        self, settings: Settings
    ) -> None:
        ca_hit = self._make_hit("ca-1")

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                side_effect=[
                    _make_query_response([ca_hit]),  # primary
                    _make_query_response([]),        # provision: no hits
                ]
            )
            mock_qdrant_cls.return_value = mock_qdrant

            results = await retrieve(
                "subsistence allowance for a union with no such table",
                union_filters=["IBEW"],
                provision_terms=["subsistence allowance"],
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 2
        assert [c.point_id for c in results] == ["ca-1"]

    @pytest.mark.asyncio
    async def test_no_provision_terms_uses_single_qdrant_call(
        self, settings: Settings
    ) -> None:
        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant_cls.return_value = mock_qdrant

            await retrieve(
                "What are the layoff notice requirements?",
                provision_terms=None,
                settings=settings,
            )

        assert mock_qdrant.query_points.await_count == 1


# ─── Structured rate lookup (issue #89) ───────────────────────────────────────


def make_wage_record(
    *,
    point_id: str = "wage-1",
    city: str = "Windsor",
    local: str = "Local 1059",
    classification_names: list[str] | None = None,
    rates: list[dict[str, Any]] | None = None,
    is_table: bool = True,
    union: str = "Labourers",
) -> MagicMock:
    """A Qdrant scroll Record for a wage-schedule classification chunk."""
    record = MagicMock()
    record.id = point_id
    record.payload = {
        "document_id": str(uuid.uuid4()),
        "source_filename": f"{union} wage schedule.pdf",
        "union_name": union,
        "document_type": "wage_schedule",
        "agreement_scope": None,
        "effective_date": "2025-05-01",
        "expiry_date": None,
        "article_number": None,
        "article_title": f"{local} {city} — JOURNEYMAN (L-12)",
        "section_number": None,
        "page_number": 3,
        "is_table": is_table,
        "text": (
            f"{union} {local} ({city}) — Labourer EPSCA Wage Schedule L-12.\n"
            "Classification: JOURNEYMAN.\n"
            "Hourly rates by effective date:\n"
            "- Effective 2025-05-01: base hourly rate $45.10, total wage package $62.35.\n"
            "- Effective 2026-05-01: base hourly rate $46.10, total wage package $63.55."
        ),
        "wage_schedule": True,
        "local": local,
        "city": city,
        "map_code": "L-12",
        "trade_name": "Labourer",
        "classification_names": classification_names or ["JOURNEYMAN"],
        "rates": rates
        if rates is not None
        else [
            {
                "effective_date": "2025-05-01",
                "sum_valid": True,
                "base hourly rate": 45.10,
                "total wage package": 62.35,
            },
            {
                "effective_date": "2026-05-01",
                "sum_valid": True,
                "base hourly rate": 46.10,
                "total wage package": 63.55,
            },
        ],
    }
    return record


class TestSelectCurrentRateRow:
    """_select_current_rate_row is pure: pick the row in effect today."""

    def test_picks_latest_in_effect_row(self) -> None:
        rows = [
            {"effective_date": "2025-05-01", "base hourly rate": 45.10},
            {"effective_date": "2026-05-01", "base hourly rate": 46.10},
            {"effective_date": "2099-05-01", "base hourly rate": 99.99},
        ]
        row = _select_current_rate_row(rows, today=date(2026, 7, 18))
        assert row is not None
        assert row["effective_date"] == "2026-05-01"

    def test_unsorted_input_still_picks_latest_in_effect(self) -> None:
        rows = [
            {"effective_date": "2026-05-01"},
            {"effective_date": "2024-05-01"},
            {"effective_date": "2025-05-01"},
        ]
        row = _select_current_rate_row(rows, today=date(2026, 7, 18))
        assert row is not None
        assert row["effective_date"] == "2026-05-01"

    def test_all_future_rows_picks_earliest(self) -> None:
        rows = [
            {"effective_date": "2099-05-01"},
            {"effective_date": "2098-05-01"},
        ]
        row = _select_current_rate_row(rows, today=date(2026, 7, 18))
        assert row is not None
        assert row["effective_date"] == "2098-05-01"

    def test_empty_rows_return_none(self) -> None:
        assert _select_current_rate_row([], today=date(2026, 7, 18)) is None

    def test_malformed_dates_are_skipped(self) -> None:
        rows = [
            {"effective_date": "not-a-date"},
            {"effective_date": "2025-05-01"},
        ]
        row = _select_current_rate_row(rows, today=date(2026, 7, 18))
        assert row is not None
        assert row["effective_date"] == "2025-05-01"


class TestStructuredRateLookup:
    """retrieve() pins a deterministically-resolved wage chunk (issue #89)."""

    QUERY = "What is the journeyperson rate for Labourers in Windsor?"

    def _run(
        self,
        scroll_pages: list[tuple[list[MagicMock], Any]],
        query: str | None = None,
        **retrieve_kwargs: Any,
    ) -> tuple[list[ChunkResult], AsyncMock]:
        """Run retrieve() with mocked Ollama + Qdrant; returns (results, qdrant)."""
        import asyncio

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(return_value=_make_query_response([]))
            mock_qdrant.scroll = AsyncMock(side_effect=scroll_pages)
            mock_qdrant_cls.return_value = mock_qdrant

            settings = Settings(
                database_url="postgresql://user:pass@localhost/epsca",
                qdrant_url="http://localhost:6333",
                ollama_url="http://localhost:11434",
                anthropic_api_key="test-key",
                jwt_secret="test-jwt-secret",  # noqa: S106
            )
            results = asyncio.run(
                retrieve(query or self.QUERY, settings=settings, **retrieve_kwargs)
            )
        return results, mock_qdrant

    def test_single_match_pins_chunk_first(self) -> None:
        record = make_wage_record()
        results, _ = self._run(
            [([record], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert results, "expected at least the pinned chunk"
        assert results[0].pinned is True
        assert results[0].point_id == "wage-1"

    def test_pinned_chunk_text_appends_current_rate_row(self) -> None:
        record = make_wage_record()
        results, _ = self._run(
            [([record], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        pinned = results[0]
        # Original verbatim text preserved, current row appended from the
        # structured payload (2026-05-01 is the latest row in effect).
        assert pinned.text.startswith("Labourers Local 1059")
        assert "Currently in effect" in pinned.text
        assert "2026-05-01" in pinned.text
        assert "$46.10" in pinned.text

    def test_local_number_match_also_pins(self) -> None:
        record = make_wage_record(city="SomewhereElse")
        results, _ = self._run(
            [([record], None)],
            query="journeyperson rate for Labourers Local 1059",
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert results[0].pinned is True

    def test_no_candidates_falls_back_without_pin(self) -> None:
        results, _ = self._run(
            [([], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert all(not c.pinned for c in results)

    def test_ambiguous_candidates_fall_back_without_pin(self) -> None:
        rec1 = make_wage_record(point_id="wage-1")
        rec2 = make_wage_record(point_id="wage-2")
        results, _ = self._run(
            [([rec1, rec2], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert all(not c.pinned for c in results)

    def test_wrong_classification_is_not_a_candidate(self) -> None:
        record = make_wage_record(
            classification_names=["FOREMAN"],
        )
        results, _ = self._run(
            [([record], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert all(not c.pinned for c in results)

    def test_no_location_in_query_falls_back(self) -> None:
        record = make_wage_record(city="Hamilton", local="Local 105")
        results, _ = self._run(
            [([record], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert all(not c.pinned for c in results)

    def test_empty_rates_falls_back(self) -> None:
        record = make_wage_record(rates=[])
        results, _ = self._run(
            [([record], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert all(not c.pinned for c in results)

    def test_scroll_filter_excludes_notes_chunks(self) -> None:
        _, mock_qdrant = self._run(
            [([], None)],
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        scroll_filter = mock_qdrant.scroll.call_args.kwargs["scroll_filter"]
        conditions = {
            (c.key, getattr(c.match, "value", None))
            for c in scroll_filter.must
            if isinstance(c, FieldCondition)
        }
        assert ("document_type", "wage_schedule") in conditions
        assert ("is_table", True) in conditions
        assert ("union_name", "Labourers") in conditions

    def test_scroll_paginates_until_offset_none(self) -> None:
        rec = make_wage_record()
        pages: list[tuple[list[MagicMock], Any]] = [
            ([make_wage_record(point_id="other", city="Hamilton")], "page-2"),
            ([rec], None),
        ]
        results, mock_qdrant = self._run(
            pages,
            union_filters=["Labourers"],
            rate_classification="journeyman",
        )
        assert mock_qdrant.scroll.await_count == 2
        assert results[0].pinned is True

    def test_no_rate_classification_skips_scroll(self) -> None:
        _, mock_qdrant = self._run(
            [([], None)],
            union_filters=["Labourers"],
            rate_classification=None,
        )
        mock_qdrant.scroll.assert_not_awaited()

    def test_multi_union_query_skips_scroll(self) -> None:
        _, mock_qdrant = self._run(
            [([], None)],
            union_filters=["Labourers", "IBEW"],
            rate_classification="journeyman",
        )
        mock_qdrant.scroll.assert_not_awaited()

    def test_pinned_respects_top_k_and_primary_floor(self) -> None:
        record = make_wage_record()
        primary_hits = []
        for i in range(TOP_K + 5):
            hit = MagicMock(spec=ScoredPoint)
            hit.id = f"ca-{i}"
            hit.score = 0.9
            hit.payload = {
                "document_id": str(uuid.uuid4()),
                "source_filename": "ca.pdf",
                "union_name": "Labourers",
                "document_type": "primary_ca",
                "agreement_scope": None,
                "effective_date": "2025-05-01",
                "expiry_date": None,
                "article_number": None,
                "article_title": None,
                "section_number": None,
                "page_number": None,
                "is_table": False,
                "text": "clause",
            }
            primary_hits.append(hit)

        import asyncio

        with (
            patch("src.rag.retrieval.httpx.AsyncClient") as mock_http,
            patch("src.rag.retrieval.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            _make_ollama_mock(mock_http)
            mock_qdrant = AsyncMock()
            mock_qdrant.query_points = AsyncMock(
                return_value=_make_query_response(primary_hits)
            )
            mock_qdrant.scroll = AsyncMock(return_value=([record], None))
            mock_qdrant_cls.return_value = mock_qdrant

            settings = Settings(
                database_url="postgresql://user:pass@localhost/epsca",
                qdrant_url="http://localhost:6333",
                ollama_url="http://localhost:11434",
                anthropic_api_key="test-key",
                jwt_secret="test-jwt-secret",  # noqa: S106
            )
            results = asyncio.run(
                retrieve(
                    self.QUERY,
                    union_filters=["Labourers"],
                    is_wage_query=True,
                    rate_classification="journeyman",
                    settings=settings,
                )
            )

        assert len(results) <= TOP_K
        assert results[0].pinned is True
        primary_count = sum(1 for c in results if c.document_type == "primary_ca")
        assert primary_count >= _MIN_PRIMARY_SLOTS
