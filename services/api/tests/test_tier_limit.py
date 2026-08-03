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
from src.auth.tier_limit import _current_month_start, enforce_tier_limit
from src.billing.plans import LAPSED_QUERY_LIMIT_MONTHLY
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
def _env(
    *,
    sub: SubscriptionRecord | None = None,
    subs: list[SubscriptionRecord] | None = None,
    used: int = 0,
) -> Iterator[AsyncMock]:
    """Patch the DB seam. ``subs`` for multi-row cases, ``sub`` for the common one."""
    rows = subs if subs is not None else ([] if sub is None else [sub])
    with patch("src.auth.tier_limit.acquire", _fake_connect), patch(
        "src.auth.tier_limit.get_tenant_subscriptions", new=AsyncMock(return_value=rows)
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


# ─── subscription status enforcement (#185) ──────────────────────────────────


def _cancelled(**overrides: Any) -> SubscriptionRecord:
    return _sub(status="cancelled", stripe_status="canceled", **overrides)


async def test_cancelled_tenant_keeps_only_the_lapsed_allowance() -> None:
    """The revenue leak: a cancelled row used to keep its full paid quota."""
    with _env(sub=_cancelled(query_limit_monthly=100), used=LAPSED_QUERY_LIMIT_MONTHLY):
        with pytest.raises(HTTPException) as exc:
            await enforce_tier_limit(_user(), _settings())
    assert exc.value.status_code == 402


async def test_cancelled_tenant_under_the_lapsed_allowance_passes() -> None:
    with _env(
        sub=_cancelled(query_limit_monthly=100), used=LAPSED_QUERY_LIMIT_MONTHLY - 1
    ):
        await enforce_tier_limit(_user(), _settings())


async def test_lapsed_allowance_resets_on_the_calendar_month() -> None:
    """A cancelled row's billing period is frozen in the past, sometimes long past.

    Counting from it would turn "10 per month" into "10 ever", which is a
    different product than the one that was decided on.
    """
    stale_period = datetime.now(UTC) - timedelta(days=90)
    with _env(
        sub=_cancelled(current_period_start=stale_period), used=0
    ) as count:
        await enforce_tier_limit(_user(), _settings())
    assert count.await_args.args[2] == _current_month_start()


async def test_past_due_within_grace_keeps_the_paid_quota() -> None:
    with _env(
        sub=_sub(
            status="past_due",
            stripe_status="past_due",
            query_limit_monthly=100,
            current_period_start=datetime.now(UTC) - timedelta(days=2),
        ),
        used=50,
    ):
        await enforce_tier_limit(_user(), _settings())


async def test_unpaid_tenant_is_cut_to_the_lapsed_allowance() -> None:
    with _env(
        sub=_sub(
            status="past_due",
            stripe_status="unpaid",
            query_limit_monthly=100,
            current_period_start=datetime.now(UTC) - timedelta(days=1),
        ),
        used=50,
    ):
        with pytest.raises(HTTPException) as exc:
            await enforce_tier_limit(_user(), _settings())
    assert exc.value.status_code == 402


async def test_active_subscription_survives_a_newer_abandoned_checkout() -> None:
    """Enforcing status must not let a stray incomplete row lock out a payer."""
    with _env(
        subs=[
            _sub(status="cancelled", stripe_status="incomplete"),
            _sub(status="active", query_limit_monthly=100),
        ],
        used=50,
    ):
        await enforce_tier_limit(_user(), _settings())


async def test_cancel_at_period_end_keeps_the_full_quota() -> None:
    with _env(
        sub=_sub(cancel_at_period_end=True, query_limit_monthly=100), used=50
    ):
        await enforce_tier_limit(_user(), _settings())
