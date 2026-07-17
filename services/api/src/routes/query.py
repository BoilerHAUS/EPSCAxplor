"""POST /query route — core RAG pipeline endpoint.

Wires together pre-processing, retrieval, context assembly, generation,
citation extraction, query logging, and the structured response.

Query logging is best-effort: the row is written after the answer is produced,
and a write failure is logged but never fails the response (``query_log_id`` is
then ``None``). Auth (tenant/user context) comes from ``get_current_user``.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from src.auth import CurrentUser, enforce_rate_limit, enforce_tier_limit, get_current_user
from src.config import Settings, get_settings
from src.db import connect
from src.db.query_logs import insert_query_log
from src.rag.citation_extractor import CitationRef, extract_citations
from src.rag.context import assemble_context
from src.rag.generator import DISCLAIMER, GeneratorResult, generate
from src.rag.preprocess import QueryContext, preprocess
from src.rag.retrieval import ChunkResult, retrieve

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be blank")
        return v


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationRef]
    model_used: str
    disclaimer: str
    query_log_id: str | None


async def _get_known_unions(database_url: str) -> list[str]:
    """Return distinct union names from the documents table."""
    conn = await asyncpg.connect(database_url, timeout=5)
    try:
        rows = await conn.fetch("SELECT DISTINCT union_name FROM documents ORDER BY union_name")
        return [row["union_name"] for row in rows]
    finally:
        await conn.close()


async def _get_title_map(database_url: str, doc_ids: list[str]) -> dict[str, str]:
    """Return a document_id → title mapping for the given UUIDs."""
    if not doc_ids:
        return {}
    conn = await asyncpg.connect(database_url, timeout=5)
    try:
        rows = await conn.fetch(
            "SELECT id::text, title FROM documents WHERE id = ANY($1::uuid[])",
            doc_ids,
        )
        return {row["id"]: row["title"] for row in rows}
    finally:
        await conn.close()


async def _write_query_log(
    database_url: str,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    query_text: str,
    response_text: str,
    model_used: str,
    union_filter: list[str] | None,
    doc_type_filter: list[str] | None,
    chunks_retrieved: int,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    citations: list[dict[str, Any]],
) -> str | None:
    """Best-effort wrapper over ``insert_query_log``; returns the id or None.

    A logging failure must never fail the user's query, so any error is logged
    and swallowed. On success the real ``query_log_id`` is returned.
    """
    try:
        async with connect(database_url) as conn:
            log_id = await insert_query_log(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                query_text=query_text,
                response_text=response_text,
                model_used=model_used,
                union_filter=union_filter,
                doc_type_filter=doc_type_filter,
                chunks_retrieved=chunks_retrieved,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                citations=citations,
            )
        return str(log_id)
    except Exception:  # noqa: BLE001
        logger.warning("query_log write failed (best-effort)", exc_info=True)
        return None


@router.post(
    "/query",
    response_model=QueryResponse,
    dependencies=[Depends(enforce_rate_limit), Depends(enforce_tier_limit)],
)
async def query_handler(
    body: QueryRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QueryResponse:
    """Execute the full RAG pipeline for a user query."""
    pipeline_start = time.monotonic()

    # Step 1 — pre-process
    known_unions = await _get_known_unions(settings.database_url)
    ctx: QueryContext = preprocess(body.query, known_unions)

    # Step 2 — retrieve
    chunks: list[ChunkResult] = await retrieve(
        body.query,
        union_filters=ctx.union_filters,
        include_nuclear_pa=ctx.include_nuclear_pa,
        agreement_scope=ctx.agreement_scope,
        is_wage_query=ctx.is_wage_query,
        settings=settings,
    )

    # Step 3 — assemble context (with title lookup)
    doc_ids = list({c.document_id for c in chunks})
    title_map = await _get_title_map(settings.database_url, doc_ids)
    context_block = assemble_context(chunks, title_map=title_map)

    # Step 4 — generate
    result: GeneratorResult = await generate(
        body.query,
        context_block,
        is_cross_union=ctx.is_cross_union,
        settings=settings,
    )

    # Step 5 — extract citations.
    # Citations come solely from resolvable [SOURCE N] markers the model wrote,
    # so a pure refusal (no markers) yields none while a partially-grounded
    # answer keeps the sources it actually referenced (see issue #119).
    citations = extract_citations(result.answer, chunks, title_map=title_map)

    # Step 6 — log query (best-effort)
    union_filter_list = ctx.union_filters or None
    doc_type_filter_list = None if ctx.include_nuclear_pa else ["primary_ca"]
    total_latency_ms = int((time.monotonic() - pipeline_start) * 1000)

    query_log_id = await _write_query_log(
        settings.database_url,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        query_text=body.query,
        response_text=result.answer,
        model_used=result.model_used,
        union_filter=union_filter_list,
        doc_type_filter=doc_type_filter_list,
        chunks_retrieved=len(chunks),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=total_latency_ms,
        citations=[c.model_dump() for c in citations],
    )

    return QueryResponse(
        answer=result.answer,
        citations=citations,
        model_used=result.model_used,
        disclaimer=DISCLAIMER,
        query_log_id=query_log_id,
    )
