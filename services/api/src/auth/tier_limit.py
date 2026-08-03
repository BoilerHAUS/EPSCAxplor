"""Per-tenant subscription tier enforcement on /query (#25, #185).

Complements the interim per-IP burst limiter (``enforce_rate_limit``) with the
business-tier monthly query quota from the ``subscriptions`` table.

This dependency guards ``/query`` and nothing else, which is deliberate: a tenant
whose subscription has lapsed can still read its past answers through ``/history``
and still list the corpus through ``/documents``. Churning does not lock a
customer out of what they already paid to produce.

**Fail-open is scoped, not blanket.** A tenant with no subscription row at all is
still unlimited — the bootstrap ``system`` tenant (migration 008) has no row, and
narrowing that would lock production out on deploy. What is no longer fail-open is
a tenant that *has* a row saying its subscription ended; see
``src.billing.entitlements`` for why those are different cases.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException

from src.auth.dependencies import CurrentUser, get_current_user
from src.billing.entitlements import resolve_entitlement, select_effective_subscription
from src.config import Settings, get_settings
from src.db import acquire
from src.db.query_logs import count_queries_since
from src.db.subscriptions import get_tenant_subscriptions


def _current_month_start() -> datetime:
    """Fallback usage window when no usable billing period applies."""
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def enforce_tier_limit(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject when the tenant is out of queries for the current period.

    429 when a paying tenant has spent its tier's allowance — the quota returns
    next period, so the request is genuinely rate-limited. 402 when a lapsed
    tenant has spent the smaller allowance it keeps after cancelling, because
    waiting will not help and paying will.

    The current request is not yet logged when this runs, so the count reflects
    prior queries — a tenant gets exactly ``query_limit_monthly`` successful
    queries per period.
    """
    now = datetime.now(UTC)
    grace_days = settings.past_due_grace_days
    async with acquire() as conn:
        subs = await get_tenant_subscriptions(conn, current_user.tenant_id)
        sub = select_effective_subscription(subs, now=now, grace_days=grace_days)
        entitlement = resolve_entitlement(sub, now=now, grace_days=grace_days)
        if entitlement.query_limit_monthly is None:
            return
        # A lapsed subscription's billing period is frozen at whenever it stopped
        # being paid for, which can be months back; counting from it would turn a
        # monthly allowance into a one-time one. Calendar months are the only
        # window that still resets for a tenant Stripe is no longer billing.
        since = _current_month_start()
        if not entitlement.is_lapsed and sub is not None and sub.current_period_start:
            since = sub.current_period_start
        used = await count_queries_since(conn, current_user.tenant_id, since)

    if used < entitlement.query_limit_monthly:
        return
    if entitlement.is_lapsed:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Your subscription is not active. The {entitlement.query_limit_monthly} "
                "free queries for this month have been used — reactivate your "
                "subscription to restore your plan's full allowance."
            ),
        )
    raise HTTPException(
        status_code=429,
        detail="Monthly query limit reached for your subscription tier.",
        headers={"Retry-After": "3600"},
    )
