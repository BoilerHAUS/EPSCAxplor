"""Tests for src/db/subscriptions.py (#25)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

from src.db.subscriptions import (
    SubscriptionRecord,
    get_tenant_subscription,
    get_tenant_subscriptions,
)


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "tier": "individual",
        "status": "active",
        "query_limit_monthly": 100,
        "user_limit": 1,
        "current_period_start": datetime.now(UTC) - timedelta(days=5),
        "current_period_end": datetime.now(UTC) + timedelta(days=25),
    }
    base.update(overrides)
    return base


async def test_get_returns_record() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=_row(tier="professional", query_limit_monthly=1000))
    sub = await get_tenant_subscription(conn, uuid.uuid4())
    assert isinstance(sub, SubscriptionRecord)
    assert sub.tier == "professional"
    assert sub.query_limit_monthly == 1000


async def test_get_returns_none_when_absent() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    assert await get_tenant_subscription(conn, uuid.uuid4()) is None


async def test_unlimited_limits_are_none() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value=_row(tier="enterprise", query_limit_monthly=None, user_limit=None)
    )
    sub = await get_tenant_subscription(conn, uuid.uuid4())
    assert sub is not None
    assert sub.query_limit_monthly is None
    assert sub.user_limit is None


async def test_stripe_columns_default_when_absent() -> None:
    """Rows written before migration 011 have neither column; both must be safe.

    ``stripe_status`` defaulting to None is what routes a hand-provisioned row
    down the "cannot tell, do not punish" path in the dunning backstop.
    """
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=_row())
    sub = await get_tenant_subscription(conn, uuid.uuid4())
    assert sub is not None
    assert sub.stripe_status is None
    assert sub.cancel_at_period_end is False


# ─── candidate-set fetch for entitlement (#185) ──────────────────────────────


async def test_get_many_returns_all_rows_in_order() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        return_value=[_row(status="active"), _row(status="cancelled")]
    )
    subs = await get_tenant_subscriptions(conn, uuid.uuid4())
    assert [s.status for s in subs] == ["active", "cancelled"]


async def test_get_many_returns_empty_list_when_absent() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    assert await get_tenant_subscriptions(conn, uuid.uuid4()) == []


async def test_get_many_floats_entitled_statuses_above_dead_rows() -> None:
    """The ORDER BY is load-bearing: it guarantees a live row is inside LIMIT.

    Asserted on the SQL because the ordering happens in Postgres, and a tenant
    with more dead rows than ``limit`` would otherwise never have its active
    subscription fetched at all.
    """
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    tenant_id = uuid.uuid4()
    await get_tenant_subscriptions(conn, tenant_id, limit=5)
    sql, *args = conn.fetch.await_args.args
    assert "ORDER BY (status IN ('active', 'trialing', 'past_due')) DESC" in sql
    assert "created_at DESC" in sql
    assert args == [tenant_id, 5]
