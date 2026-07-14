"""subscriptions persistence for per-tenant tier enforcement (#25)."""

from __future__ import annotations

import uuid
from datetime import datetime

import asyncpg
from pydantic import BaseModel


class SubscriptionRecord(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tier: str
    status: str
    query_limit_monthly: int | None  # NULL means unlimited (enterprise)
    user_limit: int | None  # NULL means unlimited
    current_period_start: datetime | None
    current_period_end: datetime | None


async def get_tenant_subscription(
    conn: asyncpg.Connection, tenant_id: uuid.UUID
) -> SubscriptionRecord | None:
    """Return the tenant's most recent subscription, or None if it has none."""
    row = await conn.fetchrow(
        "SELECT id, tenant_id, tier, status, query_limit_monthly, user_limit, "
        "current_period_start, current_period_end "
        "FROM subscriptions WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 1",
        tenant_id,
    )
    return SubscriptionRecord.model_validate(dict(row)) if row is not None else None
