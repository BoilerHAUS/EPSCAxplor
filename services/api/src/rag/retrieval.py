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

from datetime import UTC, date, datetime
from typing import Any, cast

import httpx
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Condition,
    DatetimeRange,
    FieldCondition,
    Filter,
    MatchValue,
    Record,
    ScoredPoint,
)

from src.config import Settings

COLLECTION: str = "epsca_chunks"
TOP_K: int = 10

# Guaranteed Nuclear Project Agreement chunks surfaced on nuclear-context
# queries (issue #115).  NPAs modify a base CA, so a handful of NPA chunks
# alongside the primary CA covers the nuclear-specific provisions without
# starving the CA context window.
_NUCLEAR_PA_SLOTS: int = 3
# Per-union NPA slots when a nuclear query spans multiple unions, and the
# merged cap across all detected unions.
_NUCLEAR_PA_PER_UNION: int = 2
_NUCLEAR_PA_MERGED_LIMIT: int = 4
# Floor on primary-CA chunks preserved when guaranteed secondary passes (NPA
# and/or wage) would otherwise fill the whole context window.  The base CA the
# NPA/wage chunks modify must stay present — a nuclear + cross-union rate query
# can produce enough leading chunks to displace every primary chunk otherwise.
_MIN_PRIMARY_SLOTS: int = 3

# Provision-recall (issue #78): focused key terms are re-embedded and searched
# against the existing vectors to surface the definitive clause that plain
# cosine on the full query misses.  Per-term Qdrant limit, a smaller per-term
# limit when fanning out across unions, the cap on chunks fed to ``leading``,
# and a hard cap on terms embedded per query (bounds the extra Ollama embeds +
# Qdrant round-trips this pass adds).
_PROVISION_PER_TERM: int = 3
_PROVISION_PER_UNION: int = 2
_PROVISION_MERGED_LIMIT: int = 4
_PROVISION_MAX_TERMS: int = 3

# Structured rate lookup (issue #89): scroll pagination page size and a hard
# cap on scanned points.  The corpus holds ~279 per-local wage schedules; the
# cap bounds the scan if the collection grows unexpectedly.
_RATE_SCROLL_PAGE: int = 256
_RATE_SCROLL_CAP: int = 2000


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
    # True only for the chunk resolved by the structured rate lookup (issue
    # #89) — a deterministic payload-filter match, not a similarity hit.
    pinned: bool = False


def _expiry_guard(now: datetime) -> Filter:
    """``OR(expiry_date IS NULL, expiry_date >= now)`` — exclude expired docs.

    Open-ended documents (null expiry_date) are always valid; documents with a
    future expiry_date have not yet expired.  ``is_expired`` is not stored in
    the Qdrant payload, so expiry is reconstructed from ``expiry_date`` here.
    """
    return Filter(
        should=[
            FieldCondition(key="expiry_date", is_null=True),
            FieldCondition(key="expiry_date", range=DatetimeRange(gte=now)),
        ]
    )


def _effective_guard(now: datetime) -> Filter:
    """``OR(effective_date IS NULL, effective_date <= now, wage_schedule)``.

    Excludes documents not yet in effect.  wage_schedule is exempt — multi-year
    rate tables are dated independently of the agreement lifecycle and are
    always retrieval-eligible.
    """
    return Filter(
        should=[
            FieldCondition(key="effective_date", is_null=True),
            FieldCondition(key="effective_date", range=DatetimeRange(lte=now)),
            FieldCondition(key="document_type", match=MatchValue(value="wage_schedule")),
        ]
    )


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
    must: list[Condition] = [_expiry_guard(now), _effective_guard(now)]
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
        # Null-tolerant, like the date guards: scope disambiguates unions that
        # HAVE scoped agreements (IBEW/Labourers generation vs. transmission).
        # Most unions have agreement_scope=null, and a hard match would
        # exclude them entirely — e.g. "compare IBEW Generation and Sheet
        # Metal" would silently drop all Sheet Metal chunks.
        must.append(
            Filter(
                should=[
                    FieldCondition(key="agreement_scope", is_null=True),
                    FieldCondition(
                        key="agreement_scope",
                        match=MatchValue(value=agreement_scope),
                    ),
                ]
            )
        )

    return Filter(must=must, must_not=must_not or None)


async def _query_qdrant(
    qdrant: AsyncQdrantClient,
    *,
    vector: list[float],
    union_filter: str | None,
    include_nuclear_pa: bool,
    agreement_scope: str | None,
    limit: int = TOP_K,
) -> list[ChunkResult]:
    """Run a single filtered Qdrant query and map the points to chunks."""
    response = await qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=build_filter(union_filter, include_nuclear_pa, agreement_scope),
        limit=limit,
        with_payload=True,
    )
    return [_point_to_chunk(hit) for hit in response.points]


def _merge_union_results(
    result_sets: list[list[ChunkResult]],
    *,
    limit: int = TOP_K,
) -> list[ChunkResult]:
    """Interleave per-union result sets, preserving per-union ranking.

    Each list in ``result_sets`` is assumed to already be ordered by descending
    similarity score. The merge walks those lists in rounds so multi-union
    queries keep representation from each detected union instead of letting one
    union monopolize the context window. Duplicate point IDs are removed while
    preserving the first occurrence.
    """
    merged: list[ChunkResult] = []
    seen_point_ids: set[str] = set()
    max_results = max((len(results) for results in result_sets), default=0)

    for index in range(max_results):
        for results in result_sets:
            if index >= len(results):
                continue

            chunk = results[index]
            if chunk.point_id in seen_point_ids:
                continue

            merged.append(chunk)
            seen_point_ids.add(chunk.point_id)

            if len(merged) >= limit:
                return merged

    return merged


async def _embed(text: str, settings: Settings) -> list[float]:
    """Return a 768-dim embedding for *text* via the Ollama embeddings API.

    nomic-embed-text expects task prefixes: chunks are embedded with
    "search_document: " at ingestion, queries with "search_query: " here.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": f"search_query: {text}"},
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


# Classification aliases: maps a term found in the chunk's classification
# names to the query phrasings that should select it.  Wage chunk cosine
# scores cluster within ~0.02 of each other (hundreds of near-identical rate
# tables), so exact classification/location matches must dominate ranking.
_CLASSIFICATION_ALIASES: dict[str, tuple[str, ...]] = {
    "journeyman": ("journeyperson", "journeyman", "journey person"),
    "foreman": ("foreman", "foreperson", "forewoman"),
    "subforeman": ("subforeman", "sub-foreman", "subforeperson", "sub foreman"),
    "apprentice": ("apprentice",),
    "welder": ("welder", "pipewelder"),
    "probationary": ("probationary",),
    "material handler": ("material handler",),
}
_CLASSIFICATION_BOOST = 0.15
_LOCATION_BOOST = 0.10
# Large enough to cover a full union's wage chunks (~200 for Sheet Metal) so
# the deterministic re-rank sees every candidate, not just the cosine top few.
# Union-less wage queries search the whole corpus, where high-cosine apprentice
# chunks alone can crowd out a smaller pool.
_WAGE_CANDIDATE_POOL = 1000
# Queries about a premium/differential need the journeyperson baseline in
# context alongside the named classification to compute the difference.
_PREMIUM_TERMS = ("premium", "differential", "how much more", "uplift")
_PREMIUM_BASELINE_SLOTS = 2

# A chunk's primary classification is the FIRST of these found in its
# classification names.  Order matters twice: apprentice/probationary labels
# often embed "of Journeyman Rate" (e.g. "1st Period - 40 % of Journeyman
# Rate"), so they must be checked before journeyman; and "subforeman" is a
# substring superset of "foreman".
_CLASS_PRIORITY = (
    "apprentice",
    "probationary",
    "material handler",
    "subforeman",
    "journeyman",
    "foreman",
    "welder",
)


def _chunk_classification(payload: dict[str, Any]) -> str | None:
    """Return the chunk's primary classification per _CLASS_PRIORITY."""
    names = payload.get("classification_names") or []
    if not isinstance(names, list):
        return None
    names_lower = " ".join(str(name) for name in names).lower()
    for term in _CLASS_PRIORITY:
        if term in names_lower:
            return term
    return None


def _wage_rank_boost(query_lower: str, payload: dict[str, Any]) -> float:
    """Deterministic ranking boost for wage chunks matching the query terms.

    Adds a classification boost when the query names the chunk's PRIMARY
    classification (an apprentice table whose label reads "40 % of Journeyman
    Rate" is still an apprentice table), and a location boost when the
    chunk's city or local number appears in the query.  Boosts exceed the
    cosine-score spread between wage chunks, so an exact match reliably
    outranks a lexically similar but wrong table.
    """
    boost = 0.0

    classification = _chunk_classification(payload)
    if classification is not None and any(
        alias in query_lower
        for alias in _CLASSIFICATION_ALIASES.get(classification, ())
    ):
        boost += _CLASSIFICATION_BOOST

    if _matches_location(query_lower, payload):
        boost += _LOCATION_BOOST

    return boost


def _reserve_baseline_slots(
    ranked: list[ScoredPoint],
    selected: list[ScoredPoint],
    *,
    limit: int,
) -> list[ScoredPoint]:
    """Guarantee journeyperson baseline chunks in premium-query results.

    Foreman chunks exist for every local, so on a premium query they fill
    every wage slot and the baseline needed to compute the differential
    never appears.  Reserve the last slots for the best journeyman chunks,
    preferring ones from the same locals as the already-selected chunks so
    the model can compare rates within a single schedule.
    """
    if any(_chunk_classification(hit.payload or {}) == "journeyman" for hit in selected):
        return selected

    selected_ids = {hit.id for hit in selected}
    selected_locals = {
        ((hit.payload or {}).get("local"), (hit.payload or {}).get("city"))
        for hit in selected
    }
    baselines = [
        hit
        for hit in ranked
        if hit.id not in selected_ids
        and _chunk_classification(hit.payload or {}) == "journeyman"
    ]
    baselines.sort(
        key=lambda hit: (
            ((hit.payload or {}).get("local"), (hit.payload or {}).get("city"))
            not in selected_locals,
            -hit.score,
        )
    )
    take = baselines[:_PREMIUM_BASELINE_SLOTS]
    if not take:
        return selected
    return [*selected[: limit - len(take)], *take]


def _select_current_rate_row(
    rates: list[dict[str, Any]],
    *,
    today: date,
) -> dict[str, Any] | None:
    """Return the rate row in effect on *today*, or the earliest future row.

    Rows are `{"effective_date": "YYYY-MM-DD", "sum_valid": bool, <column>:
    float, ...}` dicts from the wage chunk's structured payload.  Input order
    is not trusted; rows with unparseable dates are skipped.  Returns None
    when no row has a valid date.  Duplicate effective dates (an ingestion
    artifact) tie-break to the last such row in input order (stable sort).
    """
    dated: list[tuple[date, dict[str, Any]]] = []
    for row in rates:
        try:
            effective = date.fromisoformat(str(row.get("effective_date")))
        except (TypeError, ValueError):
            continue
        dated.append((effective, row))
    if not dated:
        return None
    dated.sort(key=lambda pair: pair[0])
    in_effect = [row for effective, row in dated if effective <= today]
    if in_effect:
        return in_effect[-1]
    return dated[0][1]


def _format_rate_row(row: dict[str, Any]) -> str:
    """Render a structured rate row as the parser's verbatim line format."""
    pairs = ", ".join(
        f"{column} ${value:.2f}"
        for column, value in row.items()
        if column not in ("effective_date", "sum_valid")
        and isinstance(value, int | float)
    )
    return f"Effective {row.get('effective_date')}: {pairs}."


def _matches_location(query_lower: str, payload: dict[str, Any]) -> bool:
    """True when the chunk's city or local number appears in the query.

    Shared by ``_wage_rank_boost`` and the structured rate lookup so the
    deterministic pin and the re-rank boost resolve location identically.
    """
    city = str(payload.get("city") or "").lower()
    local = str(payload.get("local") or "").lower()  # e.g. "local 105"
    return bool((city and city in query_lower) or (local and local in query_lower))


def _rate_lookup_filter(
    union_filter: str | None,
    agreement_scope: str | None,
) -> Filter:
    """Filter for wage-schedule TABLE chunks (notes chunks share the doc type
    but are ``is_table=False`` and must not create false ambiguity)."""
    must: list[Condition] = [
        FieldCondition(key="document_type", match=MatchValue(value="wage_schedule")),
        FieldCondition(key="is_table", match=MatchValue(value=True)),
    ]
    if union_filter:
        must.append(
            FieldCondition(key="union_name", match=MatchValue(value=union_filter))
        )
    if agreement_scope:
        # Null-tolerant, mirroring build_filter: most wage chunks are
        # scope-less and a hard match would drop them all.
        must.append(
            Filter(
                should=[
                    FieldCondition(key="agreement_scope", is_null=True),
                    FieldCondition(
                        key="agreement_scope", match=MatchValue(value=agreement_scope)
                    ),
                ]
            )
        )
    return Filter(must=must)


async def _scroll_rate_candidates(
    qdrant: AsyncQdrantClient,
    *,
    scroll_filter: Filter,
    classification: str,
    query_lower: str,
) -> Record | None:
    """Scan wage table chunks for classification + location matches.

    Returns the single matching record, or None when zero or several match
    (several = ambiguous — multiple locals/zones/map codes — so the caller
    must fall back to the re-ranked vector pass).  The scan is paginated and
    capped at ``_RATE_SCROLL_CAP`` points, with an early exit as soon as a
    second candidate appears.
    """
    match: Record | None = None
    offset: Any = None
    scanned = 0
    while True:
        records, offset = await qdrant.scroll(
            collection_name=COLLECTION,
            scroll_filter=scroll_filter,
            limit=_RATE_SCROLL_PAGE,
            offset=offset,
            with_payload=True,
        )
        for record in records:
            payload = record.payload or {}
            if _chunk_classification(payload) != classification:
                continue
            if not _matches_location(query_lower, payload):
                continue
            if match is not None:
                return None
            match = record
        scanned += len(records)
        if offset is None or not records or scanned >= _RATE_SCROLL_CAP:
            return match


def _build_pinned_chunk(record: Record) -> ChunkResult | None:
    """Build the pinned ChunkResult from a matched wage record.

    Appends a "Currently in effect" line resolved from the structured
    ``rates`` payload; returns None when no rate row has a parseable date
    (the caller then falls back to the vector pass).
    """
    payload = record.payload or {}
    rates = payload.get("rates")
    if not isinstance(rates, list):
        return None
    rows = [row for row in rates if isinstance(row, dict)]
    today = datetime.now(UTC).date()
    current_row = _select_current_rate_row(rows, today=today)
    if current_row is None:
        return None

    pinned_text = (
        f"{payload.get('text', '')}\n\n"
        f"Currently in effect (as of {today.isoformat()}): "
        f"{_format_rate_row(current_row)}"
    )
    return ChunkResult(
        point_id=str(record.id),
        # Synthetic top score: the pinned chunk is a deterministic match, not
        # a similarity hit, and must lead any downstream ordering.
        score=1.0,
        document_id=payload.get("document_id", ""),
        source_filename=payload.get("source_filename", ""),
        union_name=payload.get("union_name", ""),
        document_type=payload.get("document_type", ""),
        agreement_scope=payload.get("agreement_scope"),
        effective_date=payload.get("effective_date"),
        expiry_date=payload.get("expiry_date"),
        article_number=payload.get("article_number"),
        article_title=payload.get("article_title"),
        section_number=payload.get("section_number"),
        page_number=payload.get("page_number"),
        is_table=payload.get("is_table", True),
        text=pinned_text,
        pinned=True,
    )


async def _structured_rate_lookup(
    qdrant: AsyncQdrantClient,
    *,
    query: str,
    union_filter: str | None,
    agreement_scope: str | None,
    classification: str,
) -> ChunkResult | None:
    """Deterministically resolve ONE wage chunk by payload filter (issue #89).

    Rate questions are exact lookups, not semantic search: when the query
    names exactly one classification family and the chunk's city or local
    appears verbatim in the query, the answer lives in a single wage-schedule
    chunk whose payload already carries a structured, sum-validated ``rates``
    list.  This pass scrolls the wage-schedule table chunks (no vector),
    matches classification + location in Python, and — only when exactly one
    chunk matches — returns it as a pinned chunk with the currently-in-effect
    rate row appended from the structured payload.

    Returns None (caller falls back to the re-ranked vector pass) when zero
    or several chunks match, or when the matched chunk has no parseable rate
    rows.
    """
    record = await _scroll_rate_candidates(
        qdrant,
        scroll_filter=_rate_lookup_filter(union_filter, agreement_scope),
        classification=classification,
        query_lower=query.lower(),
    )
    if record is None:
        return None
    return _build_pinned_chunk(record)


async def _query_wage_schedules(
    qdrant: AsyncQdrantClient,
    *,
    vector: list[float],
    query: str,
    union_filter: str | None,
    agreement_scope: str | None = None,
    limit: int = 5,
) -> list[ChunkResult]:
    """Return top wage_schedule chunks regardless of general similarity rank.

    Wage schedule chunks are tabular and consistently score below CA narrative
    text in semantic search, so this secondary pass guarantees wage data
    appears in context for rate queries.  Candidates are fetched by vector
    similarity, then re-ranked with deterministic classification/location
    boosts (see _wage_rank_boost) because embedding similarity alone cannot
    distinguish e.g. a JOURNEYMAN table from an APPRENTICE table.
    """
    must: list[Condition] = [
        FieldCondition(key="document_type", match=MatchValue(value="wage_schedule")),
    ]
    if union_filter:
        must.append(
            FieldCondition(key="union_name", match=MatchValue(value=union_filter))
        )
    if agreement_scope:
        # Null-tolerant, mirroring build_filter: "generation project" queries
        # must not surface the same local's TRANSMISSION schedule (W15), but
        # unscoped unions stay eligible.
        must.append(
            Filter(
                should=[
                    FieldCondition(key="agreement_scope", is_null=True),
                    FieldCondition(
                        key="agreement_scope", match=MatchValue(value=agreement_scope)
                    ),
                ]
            )
        )
    response = await qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=Filter(must=must),
        limit=_WAGE_CANDIDATE_POOL,
        with_payload=True,
    )

    query_lower = query.lower()
    ranked = sorted(
        response.points,
        key=lambda hit: hit.score + _wage_rank_boost(query_lower, hit.payload or {}),
        reverse=True,
    )
    selected = ranked[:limit]
    if any(term in query_lower for term in _PREMIUM_TERMS):
        selected = _reserve_baseline_slots(ranked, selected, limit=limit)
    return [_point_to_chunk(hit) for hit in selected]


async def _query_nuclear_pa(
    qdrant: AsyncQdrantClient,
    *,
    vector: list[float],
    union_filter: str | None,
    agreement_scope: str | None = None,
    limit: int = _NUCLEAR_PA_SLOTS,
) -> list[ChunkResult]:
    """Return top Nuclear Project Agreement chunks by similarity.

    NPA chunks read like CA narrative but cover a smaller slice of the corpus,
    so on nuclear-context queries they are reliably out-ranked by the primary
    CA and never reach the top-k (issue #115).  This dedicated pass — mirroring
    ``_query_wage_schedules`` — guarantees NPA provisions appear in context
    alongside the primary CA.  Unlike wage schedules, NPAs need no
    deterministic re-rank: plain cosine order over the ``nuclear_pa`` subset is
    sufficient.

    NPAs are real agreements with lifecycle expiry (unlike the deliberate
    wage-schedule exemption), and this pass guarantees a leading slot — so it
    honours the same expiry/effective-date guards as the primary pass, or a
    superseded NPA could be surfaced as current.
    """
    now = datetime.now(UTC)
    must: list[Condition] = [
        _expiry_guard(now),
        _effective_guard(now),
        FieldCondition(key="document_type", match=MatchValue(value="nuclear_pa")),
    ]
    if union_filter:
        must.append(
            FieldCondition(key="union_name", match=MatchValue(value=union_filter))
        )
    if agreement_scope:
        # Null-tolerant, mirroring build_filter: NPAs are typically scope-less,
        # so a hard match would drop them; the guard keeps unscoped NPAs
        # eligible while still honouring an explicit generation/transmission
        # scope on the rare scoped NPA.
        must.append(
            Filter(
                should=[
                    FieldCondition(key="agreement_scope", is_null=True),
                    FieldCondition(
                        key="agreement_scope", match=MatchValue(value=agreement_scope)
                    ),
                ]
            )
        )
    response = await qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=Filter(must=must),
        limit=limit,
        with_payload=True,
    )
    return [_point_to_chunk(hit) for hit in response.points]


async def _query_provision_vectors(
    qdrant: AsyncQdrantClient,
    *,
    term_vectors: list[list[float]],
    union_filter: str | None,
    include_nuclear_pa: bool,
    agreement_scope: str | None = None,
    per_term_limit: int = _PROVISION_PER_TERM,
) -> list[ChunkResult]:
    """Return chunks recalled by searching pre-embedded provision-term vectors.

    Plain cosine on the full user query lands near "related" sections, not the
    definitive clause (issue #78).  Each vector is a short focused phrase (e.g.
    "double time overtime rate", "subsistence allowance") embedded by the
    caller; the per-term hits are interleaved so no single term monopolises the
    budget.  Reuses ``build_filter`` via ``_query_qdrant`` so expiry/effective/
    union/scope guards and nuclear eligibility are inherited — the pass is
    doc-type-agnostic within eligibility because the definitive chunk may be
    primary_ca (O07/W02/T03) or nuclear_pa (N02).

    Takes pre-computed vectors (not raw terms) so the caller embeds each term
    once and reuses it across per-union fan-out queries.
    """
    term_sets: list[list[ChunkResult]] = []
    for vector in term_vectors:
        term_sets.append(
            await _query_qdrant(
                qdrant,
                vector=vector,
                union_filter=union_filter,
                include_nuclear_pa=include_nuclear_pa,
                agreement_scope=agreement_scope,
                limit=per_term_limit,
            )
        )
    return _merge_union_results(term_sets, limit=_PROVISION_MERGED_LIMIT)


def _merge_with_priority(
    primary: list[ChunkResult],
    leading: list[ChunkResult],
    *,
    limit: int = TOP_K,
) -> list[ChunkResult]:
    """Combine primary results with guaranteed *leading* chunks, deduplicating
    by point_id.

    ``leading`` chunks come from dedicated secondary passes (wage schedules,
    Nuclear Project Agreements) that consistently score below CA narrative
    text, so they are placed first to guarantee a place in the context window.
    Remaining slots are filled from the primary results.
    """
    seen: set[str] = set()
    merged: list[ChunkResult] = []
    for chunk in [*leading, *primary]:
        if chunk.point_id not in seen:
            seen.add(chunk.point_id)
            merged.append(chunk)
        if len(merged) >= limit:
            break
    return merged


async def _collect_wage_chunks(
    qdrant: AsyncQdrantClient,
    *,
    vector: list[float],
    query: str,
    union_filters: list[str],
    agreement_scope: str | None,
) -> list[ChunkResult]:
    """Run the wage-schedule secondary pass, fanning out per union for
    multi-union queries so each union's re-ranked wage chunks are represented
    instead of one union's high-cosine tables monopolizing the wage slots.
    """
    if len(union_filters) > 1:
        wage_sets = [
            await _query_wage_schedules(
                qdrant,
                vector=vector,
                query=query,
                union_filter=union_filter,
                agreement_scope=agreement_scope,
                limit=3,
            )
            for union_filter in union_filters
        ]
        return _merge_union_results(wage_sets, limit=6)
    union_filter = union_filters[0] if union_filters else None
    return await _query_wage_schedules(
        qdrant,
        vector=vector,
        query=query,
        union_filter=union_filter,
        agreement_scope=agreement_scope,
    )


async def _collect_nuclear_pa_chunks(
    qdrant: AsyncQdrantClient,
    *,
    vector: list[float],
    union_filters: list[str],
    agreement_scope: str | None,
) -> list[ChunkResult]:
    """Run the NPA secondary pass, fanning out per union for multi-union
    nuclear queries so each named union's NPA chunks are represented — and NPAs
    from unions not named in the query are not pulled in by an unfiltered pass.
    """
    if len(union_filters) > 1:
        npa_sets = [
            await _query_nuclear_pa(
                qdrant,
                vector=vector,
                union_filter=union_filter,
                agreement_scope=agreement_scope,
                limit=_NUCLEAR_PA_PER_UNION,
            )
            for union_filter in union_filters
        ]
        return _merge_union_results(npa_sets, limit=_NUCLEAR_PA_MERGED_LIMIT)
    union_filter = union_filters[0] if union_filters else None
    return await _query_nuclear_pa(
        qdrant,
        vector=vector,
        union_filter=union_filter,
        agreement_scope=agreement_scope,
    )


async def _collect_provision_chunks(
    qdrant: AsyncQdrantClient,
    *,
    terms: list[str],
    settings: Settings,
    union_filters: list[str],
    include_nuclear_pa: bool,
    agreement_scope: str | None,
) -> list[ChunkResult]:
    """Run the provision-recall pass, fanning out per union for multi-union
    queries so each named union's specific provision is represented — and
    provisions from unions not named in the query are not pulled in by an
    unfiltered pass.

    Each term is embedded once (capped at ``_PROVISION_MAX_TERMS`` to bound the
    added Ollama round-trips) and the resulting vectors are reused across the
    per-union fan-out, so a K-union query still embeds only the distinct terms.
    """
    term_vectors = [await _embed(term, settings) for term in terms[:_PROVISION_MAX_TERMS]]
    if len(union_filters) > 1:
        provision_sets = [
            await _query_provision_vectors(
                qdrant,
                term_vectors=term_vectors,
                union_filter=union_filter,
                include_nuclear_pa=include_nuclear_pa,
                agreement_scope=agreement_scope,
                per_term_limit=_PROVISION_PER_UNION,
            )
            for union_filter in union_filters
        ]
        return _merge_union_results(provision_sets, limit=_PROVISION_MERGED_LIMIT)
    union_filter = union_filters[0] if union_filters else None
    return await _query_provision_vectors(
        qdrant,
        term_vectors=term_vectors,
        union_filter=union_filter,
        include_nuclear_pa=include_nuclear_pa,
        agreement_scope=agreement_scope,
    )


async def retrieve(
    query: str,
    *,
    union_filters: list[str] | None = None,
    include_nuclear_pa: bool = False,
    agreement_scope: str | None = None,
    is_wage_query: bool = False,
    provision_terms: list[str] | None = None,
    rate_classification: str | None = None,
    settings: Settings,
) -> list[ChunkResult]:
    """Embed *query* and retrieve the top-k matching chunks from Qdrant.

    Args:
        query: The raw user question to embed and search against.
        union_filters: When set, restrict retrieval to the given unions. A
            single detected union behaves like the previous single-filter path.
            Multiple detected unions trigger one filtered retrieval per union,
            then a deterministic merged result list.
        include_nuclear_pa: When ``True``, make NPA chunks eligible in the
            primary pass and run a secondary retrieval pass restricted to
            Nuclear Project Agreement chunks, prepending those so NPA
            provisions are guaranteed to appear alongside the primary CA
            (issue #115).  Defaults to ``False``; set to ``True`` when the query
            contains nuclear-site context (see ``preprocess.detect_nuclear``).
        agreement_scope: Restrict to ``"generation"`` or ``"transmission"``
            for IBEW / Labourers queries.
        is_wage_query: When ``True``, run a secondary wage_schedule-focused
            retrieval pass and prepend those chunks so tabular rate data is
            guaranteed to appear in the context window.
        provision_terms: Focused key phrases (from
            ``preprocess.detect_provision_terms``) re-embedded as secondary
            query vectors to recall a specific provision that plain cosine on
            the full query misses (issue #78).  When non-empty, these chunks
            lead the context window ahead of the NPA and wage passes.
        rate_classification: Single classification family (from
            ``preprocess.detect_rate_classification``) that activates the
            structured rate lookup (issue #89).  When the classification plus
            the query's city/local resolve to exactly one wage chunk, that
            chunk is pinned at the head of the context window; otherwise the
            existing re-ranked wage pass is the sole wage source.  Skipped for
            multi-union queries.
        settings: Application settings providing Qdrant and Ollama URLs.

    Returns:
        Up to ``TOP_K`` ``ChunkResult`` objects ordered by descending cosine
        similarity score for single-union queries, or a deterministic
        interleaving of per-union top results for multi-union queries.
    """
    vector = await _embed(query, settings)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    unique_union_filters = list(dict.fromkeys(union_filters or []))
    if len(unique_union_filters) > 1:
        result_sets = [
            await _query_qdrant(
                qdrant,
                vector=vector,
                union_filter=union_filter,
                include_nuclear_pa=include_nuclear_pa,
                agreement_scope=agreement_scope,
            )
            for union_filter in unique_union_filters
        ]
        primary = _merge_union_results(result_sets)
    else:
        union_filter = unique_union_filters[0] if unique_union_filters else None
        primary = await _query_qdrant(
            qdrant,
            vector=vector,
            union_filter=union_filter,
            include_nuclear_pa=include_nuclear_pa,
            agreement_scope=agreement_scope,
        )

    # Secondary guaranteed passes.  Provision-recall terms, NPAs, and wage
    # tables all get crowded out of the primary top-k, so each gets a dedicated
    # pass whose chunks lead the merged context window.  The passes are
    # round-robin interleaved (not concatenated): the first chunk of each still
    # leads in priority order (provision → NPA → wage), but no earlier pass can
    # starve a later one out of the window — e.g. provision + NPA hits filling
    # every slot and dropping the guaranteed wage table on a rate query.
    leading_sets: list[list[ChunkResult]] = []
    if rate_classification and len(unique_union_filters) <= 1:
        pinned = await _structured_rate_lookup(
            qdrant,
            query=query,
            union_filter=unique_union_filters[0] if unique_union_filters else None,
            agreement_scope=agreement_scope,
            classification=rate_classification,
        )
        if pinned is not None:
            # Highest-priority leading set: the deterministic rate match leads
            # the context window ahead of provision/NPA/wage chunks.
            leading_sets.append([pinned])
    if provision_terms:
        leading_sets.append(
            await _collect_provision_chunks(
                qdrant,
                terms=provision_terms,
                settings=settings,
                union_filters=unique_union_filters,
                include_nuclear_pa=include_nuclear_pa,
                agreement_scope=agreement_scope,
            )
        )
    if include_nuclear_pa:
        leading_sets.append(
            await _collect_nuclear_pa_chunks(
                qdrant,
                vector=vector,
                union_filters=unique_union_filters,
                agreement_scope=agreement_scope,
            )
        )
    if is_wage_query:
        leading_sets.append(
            await _collect_wage_chunks(
                qdrant,
                vector=vector,
                query=query,
                union_filters=unique_union_filters,
                agreement_scope=agreement_scope,
            )
        )

    if not any(leading_sets):
        return primary
    # Reserve a floor of primary-CA slots so the base agreement is never fully
    # displaced by the guaranteed leading chunks — a nuclear cross-union rate
    # query can otherwise produce TOP_K leading chunks and zero CA context.
    reserve = min(_MIN_PRIMARY_SLOTS, len(primary))
    leading = _merge_union_results(leading_sets, limit=TOP_K - reserve)
    return _merge_with_priority(primary, leading)
