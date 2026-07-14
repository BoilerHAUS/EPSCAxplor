"""Tests for usage counters: count_queries_since, count_users_for_tenant (#25)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from src.db.query_logs import count_queries_since
from src.db.users import count_users_for_tenant


async def test_count_queries_since_targets_tenant_and_time() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=7)
    since = datetime.now(UTC) - timedelta(days=1)
    tid = uuid.uuid4()
    assert await count_queries_since(conn, tid, since) == 7
    args = conn.fetchval.await_args.args
    assert args[1] == tid
    assert args[2] == since


async def test_count_users_for_tenant_returns_int() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=3)
    tid = uuid.uuid4()
    assert await count_users_for_tenant(conn, tid) == 3
    assert conn.fetchval.await_args.args[1] == tid
