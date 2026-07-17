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

    city = str(payload.get("city") or "").lower()
    local = str(payload.get("local") or "").lower()  # e.g. "local 105"
    if (city and city in query_lower) or (local and local in query_lower):
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


async def retrieve(
    query: str,
    *,
    union_filters: list[str] | None = None,
    include_nuclear_pa: bool = False,
    agreement_scope: str | None = None,
    is_wage_query: bool = False,
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
        settings: Application settings providing Qdrant and Ollama URLs.

    Returns:
        Up to ``TOP_K`` ``ChunkResult`` objects ordered by descending cosine
        similarity score for single-union queries, or a deterministic
        interleaving of per-union top results for multi-union queries.
    """
    vector = await _embed(query, settings)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)

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

    # Secondary guaranteed passes.  Wage tables and NPAs both score below CA
    # narrative and get crowded out of the primary top-k, so each detected type
    # gets a dedicated pass whose chunks lead the merged context window.  NPAs
    # are collected before wage chunks so nuclear provisions lead on a query
    # that is both nuclear- and rate-focused.
    leading: list[ChunkResult] = []
    if include_nuclear_pa:
        leading.extend(
            await _collect_nuclear_pa_chunks(
                qdrant,
                vector=vector,
                union_filters=unique_union_filters,
                agreement_scope=agreement_scope,
            )
        )
    if is_wage_query:
        leading.extend(
            await _collect_wage_chunks(
                qdrant,
                vector=vector,
                query=query,
                union_filters=unique_union_filters,
                agreement_scope=agreement_scope,
            )
        )

    if not leading:
        return primary
    # Reserve a floor of primary-CA slots so the base agreement is never fully
    # displaced by the guaranteed NPA/wage chunks — a nuclear cross-union rate
    # query can otherwise produce TOP_K leading chunks and zero CA context.
    reserve = min(_MIN_PRIMARY_SLOTS, len(primary))
    return _merge_with_priority(primary, leading[: TOP_K - reserve])
