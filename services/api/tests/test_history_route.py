"""Tests for src/routes/history.py — GET /query-history (#26)."""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.auth import CurrentUser
from src.config import Settings
from src.db.query_logs import QueryLogListItem
from src.routes.history import QueryHistoryResponse, query_history_route


def _settings() -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="hist-test-secret",
    )


def _user(tenant_id: uuid.UUID | None = None) -> CurrentUser:
    return CurrentUser(tenant_id=tenant_id or uuid.uuid4(), user_id=uuid.uuid4())


def _log(**overrides: Any) -> QueryLogListItem:
    base: dict[str, Any] = dict(
        id=uuid.uuid4(),
        query_text="q",
        response_text="a [SOURCE 1]",
        model_used="claude-haiku-4-5-20251001",
        citations=[{"source_number": 1}],
        created_at=datetime.now(UTC),
    )
    base.update(overrides)
    return QueryLogListItem(**base)


@contextlib.asynccontextmanager
async def _fake_connect(*_a: object, **_k: object) -> Any:
    yield AsyncMock()


async def test_returns_history_with_pagination() -> None:
    logs = [_log(), _log(query_text="q2")]
    with patch("src.routes.history.connect", _fake_connect), patch(
        "src.routes.history.list_query_logs", new=AsyncMock(return_value=logs)
    ), patch("src.routes.history.count_query_logs", new=AsyncMock(return_value=5)):
        resp = await query_history_route(
            current_user=_user(), settings=_settings(), limit=20, offset=0
        )
    assert isinstance(resp, QueryHistoryResponse)
    assert resp.total == 5
    assert resp.limit == 20
    assert resp.offset == 0
    assert len(resp.queries) == 2
    assert resp.queries[0].answer == "a [SOURCE 1]"  # response_text mapped to answer


async def test_scopes_queries_and_count_to_caller_tenant() -> None:
    tenant_id = uuid.uuid4()
    with patch("src.routes.history.connect", _fake_connect), patch(
        "src.routes.history.list_query_logs", new=AsyncMock(return_value=[])
    ) as listed, patch(
        "src.routes.history.count_query_logs", new=AsyncMock(return_value=0)
    ) as counted:
        await query_history_route(
            current_user=_user(tenant_id), settings=_settings(), limit=20, offset=0
        )
    assert listed.await_args.args[1] == tenant_id
    assert counted.await_args.args[1] == tenant_id


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/query-history").status_code == 401
