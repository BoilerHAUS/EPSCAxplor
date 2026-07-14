"""Per-tenant subscription tier enforcement on /query (#25).

Complements the interim per-IP burst limiter (``enforce_rate_limit``) with the
business-tier monthly query quota from the ``subscriptions`` table. Fails open
when a tenant has no subscription or an unlimited (enterprise) quota, so it stays
inert until subscriptions exist (Stripe integration is #32).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException

from src.auth.dependencies import CurrentUser, get_current_user
from src.config import Settings, get_settings
from src.db import connect
from src.db.query_logs import count_queries_since
from src.db.subscriptions import get_tenant_subscription


def _current_month_start() -> datetime:
    """Fallback usage window when a subscription has no explicit billing period."""
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def enforce_tier_limit(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject with 429 when the tenant has hit its monthly query quota.

    Fail-open: no subscription, or a NULL ``query_limit_monthly`` (enterprise),
    means unlimited. The current request is not yet logged when this runs, so the
    count reflects prior queries — a tenant gets exactly ``query_limit_monthly``
    successful queries per period.
    """
    async with connect(settings.database_url) as conn:
        sub = await get_tenant_subscription(conn, current_user.tenant_id)
        if sub is None or sub.query_limit_monthly is None:
            return
        since = sub.current_period_start or _current_month_start()
        used = await count_queries_since(conn, current_user.tenant_id, since)
    if used >= sub.query_limit_monthly:
        raise HTTPException(
            status_code=429,
            detail="Monthly query limit reached for your subscription tier.",
            headers={"Retry-After": "3600"},
        )
