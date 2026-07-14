"""Tests for list_query_logs / count_query_logs in src/db/query_logs.py (#26)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from src.db.query_logs import QueryLogListItem, count_query_logs, list_query_logs


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "query_text": "what is overtime?",
        "response_text": "answer [SOURCE 1]",
        "model_used": "claude-haiku-4-5-20251001",
        "citations": json.dumps([{"source_number": 1, "union_name": "IBEW"}]),
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return base


async def test_list_parses_citations_and_binds_pagination() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[_row()])
    tid = uuid.uuid4()
    items = await list_query_logs(conn, tid, limit=20, offset=5)
    assert len(items) == 1
    assert isinstance(items[0], QueryLogListItem)
    assert items[0].citations == [{"source_number": 1, "union_name": "IBEW"}]
    args = conn.fetch.await_args.args  # SQL, tenant_id, limit, offset
    assert args[1] == tid
    assert args[2] == 20
    assert args[3] == 5


async def test_list_handles_null_citations() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[_row(citations=None)])
    items = await list_query_logs(conn, uuid.uuid4(), limit=10, offset=0)
    assert items[0].citations == []


async def test_count_returns_int_scoped_to_tenant() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=42)
    tid = uuid.uuid4()
    assert await count_query_logs(conn, tid) == 42
    assert conn.fetchval.await_args.args[1] == tid
