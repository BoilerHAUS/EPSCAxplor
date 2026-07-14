"""Tests for src/db/subscriptions.py (#25)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

from src.db.subscriptions import SubscriptionRecord, get_tenant_subscription


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
