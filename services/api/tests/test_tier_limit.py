"""Tests for src/auth/tier_limit.py — per-tenant tier enforcement (#25)."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.auth.dependencies import CurrentUser
from src.auth.tier_limit import enforce_tier_limit
from src.config import Settings
from src.db.subscriptions import SubscriptionRecord


def _settings() -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="tier-test-secret",
    )


def _user() -> CurrentUser:
    return CurrentUser(tenant_id=uuid.uuid4(), user_id=uuid.uuid4())


def _sub(**overrides: Any) -> SubscriptionRecord:
    base: dict[str, Any] = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tier="individual",
        status="active",
        query_limit_monthly=100,
        user_limit=1,
        current_period_start=datetime.now(UTC) - timedelta(days=3),
        current_period_end=datetime.now(UTC) + timedelta(days=27),
    )
    base.update(overrides)
    return SubscriptionRecord(**base)


@contextlib.asynccontextmanager
async def _fake_connect(*_a: object, **_k: object) -> Any:
    yield AsyncMock()


@contextlib.contextmanager
def _env(*, sub: SubscriptionRecord | None, used: int = 0) -> Iterator[AsyncMock]:
    with patch("src.auth.tier_limit.connect", _fake_connect), patch(
        "src.auth.tier_limit.get_tenant_subscription", new=AsyncMock(return_value=sub)
    ), patch(
        "src.auth.tier_limit.count_queries_since", new=AsyncMock(return_value=used)
    ) as count:
        yield count


async def test_no_subscription_passes_without_counting() -> None:
    with _env(sub=None) as count:
        await enforce_tier_limit(_user(), _settings())
    count.assert_not_awaited()


async def test_enterprise_unlimited_passes_without_counting() -> None:
    with _env(sub=_sub(tier="enterprise", query_limit_monthly=None)) as count:
        await enforce_tier_limit(_user(), _settings())
    count.assert_not_awaited()


async def test_under_limit_passes() -> None:
    with _env(sub=_sub(query_limit_monthly=100), used=99):
        await enforce_tier_limit(_user(), _settings())


async def test_at_limit_raises_429() -> None:
    with _env(sub=_sub(query_limit_monthly=100), used=100):
        with pytest.raises(HTTPException) as exc:
            await enforce_tier_limit(_user(), _settings())
    assert exc.value.status_code == 429


async def test_over_limit_raises_429() -> None:
    with _env(sub=_sub(query_limit_monthly=50), used=200):
        with pytest.raises(HTTPException) as exc:
            await enforce_tier_limit(_user(), _settings())
    assert exc.value.status_code == 429


async def test_counts_from_subscription_period_start() -> None:
    period_start = datetime.now(UTC) - timedelta(days=10)
    with _env(
        sub=_sub(query_limit_monthly=100, current_period_start=period_start), used=1
    ) as count:
        await enforce_tier_limit(_user(), _settings())
    # count_queries_since(conn, tenant_id, since) — since is the 3rd positional arg
    assert count.await_args.args[2] == period_start
