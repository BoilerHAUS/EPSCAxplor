"""Tests for src/db/query_logs.py (#88)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

from src.db.query_logs import insert_query_log

CITATIONS = [{"source_number": 1, "union_name": "IBEW"}]


async def test_insert_returns_id_and_serializes_citations() -> None:
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": new_id})
    got = await insert_query_log(
        conn,
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        query_text="q",
        response_text="r",
        model_used="claude-haiku-4-5-20251001",
        union_filter=["IBEW"],
        doc_type_filter=["primary_ca"],
        chunks_retrieved=6,
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=250,
        citations=CITATIONS,
    )
    assert got == new_id
    conn.fetchrow.assert_awaited_once()
    # citations are serialized to a JSON string for the jsonb column (last positional arg)
    assert json.loads(conn.fetchrow.await_args.args[-1]) == CITATIONS


async def test_insert_accepts_null_user_id_and_empty_filters() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": uuid.uuid4()})
    await insert_query_log(
        conn,
        tenant_id=uuid.uuid4(),
        user_id=None,
        query_text="q",
        response_text="r",
        model_used="m",
        union_filter=None,
        doc_type_filter=None,
        chunks_retrieved=0,
        prompt_tokens=0,
        completion_tokens=0,
        latency_ms=0,
        citations=[],
    )
    args = conn.fetchrow.await_args.args
    # args[0]=SQL, args[1]=tenant_id, args[2]=user_id, ..., args[-1]=citations JSON
    assert args[2] is None
    assert json.loads(args[-1]) == []
