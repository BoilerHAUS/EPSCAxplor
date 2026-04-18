"""RAG retrieval layer for EPSCAxplor.

Step 2 of the query pipeline: embed the user query via Ollama then execute a
filtered similarity search against Qdrant, returning the top-k chunks.

Design notes
------------
* ``is_expired`` is absent from the Qdrant payload (store.py never writes it).
  The expiry guard is therefore reconstructed from ``expiry_date``: chunks with
  a null expiry_date (open-ended agreements) are always included; chunks with a
  future expiry_date pass the filter; chunks with a past expiry_date are
  excluded.  Qdrant's DatetimeRange works with RFC 3339 / ISO 8601 strings; the
  payload values ("2030-04-30") satisfy ISO 8601 so the filter is applied
  correctly.  If Qdrant cannot parse a value as a datetime it skips the filter
  rather than raising an error, which is acceptable since the current corpus
  contains no expired documents.

* ``title`` is absent from the Qdrant payload (store.py never writes it).
  ``ChunkResult`` exposes ``source_filename`` as a fallback.  Callers that need
  the human-readable document title should look it up in PostgreSQL by
  ``document_id`` and pass it to ``assemble_context`` via ``title_map``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import httpx
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Condition,
    DatetimeRange,
    FieldCondition,
    Filter,
    MatchValue,
    ScoredPoint,
)

from src.config import Settings

COLLECTION: str = "epsca_chunks"
TOP_K: int = 6


class ChunkResult(BaseModel):
    """A single retrieved chunk with its Qdrant payload and similarity score."""

    point_id: str
    score: float
    document_id: str
    source_filename: str
    union_name: str
    document_type: str
    agreement_scope: str | None
    effective_date: str | None
    expiry_date: str | None
    article_number: str | None
    article_title: str | None
    section_number: str | None
    page_number: int | None
    is_table: bool
    text: str


def build_filter(
    union_filter: str | None,
    include_nuclear_pa: bool,
    agreement_scope: str | None,
) -> Filter:
    """Construct a Qdrant filter from retrieval parameters.

    The filter is composed as ``AND(expiry_guard, *optional_conditions)``.

    The expiry guard is ``OR(expiry_date IS NULL, expiry_date >= now)`` and is
    always applied.  It replaces the ``is_expired = false`` condition from the
    planning spec because ``is_expired`` is not stored in the Qdrant payload.

    Args:
        union_filter: When set, restrict to chunks whose ``union_name`` exactly
            matches this value.
        include_nuclear_pa: When ``False`` (default), restrict
            ``document_type`` to ``primary_ca``.  When ``True``, all document
            types — including Nuclear Project Agreements — are eligible.
        agreement_scope: When set, restrict to ``"generation"`` or
            ``"transmission"`` (relevant for IBEW and Labourers agreements).

    Returns:
        A ``qdrant_client.models.Filter`` ready for use in a search request.
    """
    now = datetime.now(UTC)

    # Expiry guard: open-ended documents (null expiry_date) are always valid;
    # documents with a future expiry_date have not yet expired.
    expiry_guard = Filter(
        should=[
            FieldCondition(key="expiry_date", is_null=True),
            FieldCondition(
                key="expiry_date",
                range=DatetimeRange(gte=now),
            ),
        ]
    )

    # Effective-date guard: exclude documents not yet in effect (e.g. 2026 wage
    # schedules returned for a query about current/2025 rates).
    effective_guard = Filter(
        should=[
            FieldCondition(key="effective_date", is_null=True),
            FieldCondition(
                key="effective_date",
                range=DatetimeRange(lte=now),
            ),
        ]
    )

    must: list[Condition] = [expiry_guard, effective_guard]
    must_not: list[Condition] = []

    if union_filter:
        must.append(
            FieldCondition(key="union_name", match=MatchValue(value=union_filter))
        )

    if not include_nuclear_pa:
        # Exclude NPAs unless the query explicitly references nuclear context.
        # Use must_not so wage_schedule and other non-NPA types remain eligible.
        must_not.append(
            FieldCondition(
                key="document_type",
                match=MatchValue(value="nuclear_pa"),
            )
        )

    if agreement_scope:
        must.append(
            FieldCondition(
                key="agreement_scope",
                match=MatchValue(value=agreement_scope),
            )
        )

    return Filter(must=must, must_not=must_not or None)


async def _embed(text: str, settings: Settings) -> list[float]:
    """Return a 768-dim embedding for *text* via the Ollama embeddings API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
            timeout=30.0,
        )
        response.raise_for_status()
    data = response.json()
    return cast(list[float], data.get("embedding", []))


def _point_to_chunk(point: ScoredPoint) -> ChunkResult:
    """Convert a Qdrant ScoredPoint to a ChunkResult."""
    p = point.payload or {}
    return ChunkResult(
        point_id=str(point.id),
        score=point.score,
        document_id=p.get("document_id", ""),
        source_filename=p.get("source_filename", ""),
        union_name=p.get("union_name", ""),
        document_type=p.get("document_type", ""),
        agreement_scope=p.get("agreement_scope"),
        effective_date=p.get("effective_date"),
        expiry_date=p.get("expiry_date"),
        article_number=p.get("article_number"),
        article_title=p.get("article_title"),
        section_number=p.get("section_number"),
        page_number=p.get("page_number"),
        is_table=p.get("is_table", False),
        text=p.get("text", ""),
    )


async def retrieve(
    query: str,
    *,
    union_filter: str | None = None,
    include_nuclear_pa: bool = False,
    agreement_scope: str | None = None,
    settings: Settings,
) -> list[ChunkResult]:
    """Embed *query* and retrieve the top-k matching chunks from Qdrant.

    Args:
        query: The raw user question to embed and search against.
        union_filter: When set, restrict retrieval to a single union by name.
        include_nuclear_pa: Include Nuclear Project Agreement chunks when
            ``True``.  Defaults to ``False``; set to ``True`` when the query
            contains nuclear-site context (see ``preprocess.detect_nuclear``).
        agreement_scope: Restrict to ``"generation"`` or ``"transmission"``
            for IBEW / Labourers queries.
        settings: Application settings providing Qdrant and Ollama URLs.

    Returns:
        Up to ``TOP_K`` ``ChunkResult`` objects ordered by descending cosine
        similarity score.
    """
    vector = await _embed(query, settings)
    filt = build_filter(union_filter, include_nuclear_pa, agreement_scope)

    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    response = await qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=filt,
        limit=TOP_K,
        with_payload=True,
    )
    return [_point_to_chunk(hit) for hit in response.points]
