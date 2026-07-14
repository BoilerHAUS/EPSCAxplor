"""query_logs persistence — the append-only audit row written for every /query.

Takes a caller-provided asyncpg connection (see ``src.db.connect``) and raises on
failure; the route wraps it in a best-effort guard so a logging hiccup never fails
a user's answer.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import asyncpg


async def insert_query_log(
    conn: asyncpg.Connection,
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
) -> uuid.UUID:
    """Insert one query_logs row and return its id."""
    row = await conn.fetchrow(
        """
        INSERT INTO query_logs (
            tenant_id, user_id, query_text, response_text, model_used,
            union_filter, doc_type_filter, chunks_retrieved,
            prompt_tokens, completion_tokens, latency_ms, citations
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id
        """,
        tenant_id,
        user_id,
        query_text,
        response_text,
        model_used,
        union_filter,
        doc_type_filter,
        chunks_retrieved,
        prompt_tokens,
        completion_tokens,
        latency_ms,
        json.dumps(citations),
    )
    log_id: uuid.UUID = row["id"]
    return log_id


async def count_queries_since(
    conn: asyncpg.Connection, tenant_id: uuid.UUID, since: datetime
) -> int:
    """Count a tenant's queries since a timestamp (usage in the current period)."""
    count = await conn.fetchval(
        "SELECT count(*) FROM query_logs WHERE tenant_id = $1 AND created_at >= $2",
        tenant_id,
        since,
    )
    return int(count)
