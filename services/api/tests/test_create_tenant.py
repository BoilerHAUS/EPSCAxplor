"""Tests for scripts/create_tenant.py — the operator tenant-seeding CLI (#31)."""

from __future__ import annotations

import contextlib
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from scripts.create_tenant import _create_tenant, _parse_args, _resolve_database_url


def test_parse_args_reads_core_fields() -> None:
    args = _parse_args(["--name", "Tenant A", "--slug", "tenant-a", "--tier", "professional"])
    assert args.name == "Tenant A"
    assert args.slug == "tenant-a"
    assert args.tier == "professional"
    assert args.query_limit_monthly is None
    assert args.user_limit is None


def test_parse_args_rejects_invalid_tier() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--name", "X", "--slug", "x", "--tier", "platinum"])


def test_resolve_database_url_prefers_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    assert _resolve_database_url("postgresql://explicit") == "postgresql://explicit"


def test_resolve_database_url_errors_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    with pytest.raises(SystemExit):
        _resolve_database_url(None)


async def test_create_tenant_inserts_without_subscription() -> None:
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[None, new_id])  # no existing slug, then INSERT id
    conn.execute = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_tenant.connect", _fake_connect):
        tenant_id, subscription_created = await _create_tenant(
            name="Tenant A",
            slug="tenant-a",
            tier="professional",
            query_limit_monthly=None,
            user_limit=None,
            database_url="postgresql://x",
        )

    assert tenant_id == new_id
    assert subscription_created is False
    conn.execute.assert_not_awaited()  # no subscription row when no limits given


async def test_create_tenant_attaches_subscription_when_limit_set() -> None:
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[None, new_id])
    conn.execute = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_tenant.connect", _fake_connect):
        _, subscription_created = await _create_tenant(
            name="Rate Test",
            slug="rate-test",
            tier="professional",
            query_limit_monthly=3,
            user_limit=None,
            database_url="postgresql://x",
        )

    assert subscription_created is True
    conn.execute.assert_awaited_once()
    args = conn.execute.await_args.args
    assert args[1] == new_id  # tenant_id
    assert args[2] == "professional"  # subscription tier mirrors tenant tier
    assert args[3] == 3  # query_limit_monthly
    assert args[4] is None  # user_limit


async def test_create_tenant_errors_when_slug_exists() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=uuid.uuid4())  # slug already taken
    conn.execute = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_tenant.connect", _fake_connect):
        with pytest.raises(SystemExit):
            await _create_tenant(
                name="Dup",
                slug="system",
                tier="enterprise",
                query_limit_monthly=None,
                user_limit=None,
                database_url="postgresql://x",
            )

    assert conn.fetchval.await_count == 1  # existence check only, no INSERT
    conn.execute.assert_not_awaited()
