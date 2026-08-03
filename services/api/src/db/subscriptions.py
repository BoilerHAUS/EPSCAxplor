"""subscriptions persistence for per-tenant tier enforcement (#25) and the
Stripe webhook sync that populates it (#32)."""

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


# ─── Stripe webhook sync (#32) ───────────────────────────────────────────────


async def claim_stripe_event(
    conn: asyncpg.Connection, event_id: str, event_type: str
) -> bool:
    """Claim a Stripe event id, returning False if it was already processed.

    Stripe delivers AT LEAST ONCE: it retries any non-2xx or timed-out delivery,
    and occasionally re-sends an event whose 200 was lost in transit. Rather than
    making each handler independently replay-safe, the caller claims the id here
    and skips the handler entirely when the claim is refused.

    ``ON CONFLICT DO NOTHING RETURNING`` makes this atomic under the primary
    key's unique index, so exactly one of two concurrent deliveries of the same
    event proceeds — which is what makes it correct when a retry overlaps the
    original delivery rather than following it.

    CALLER CONTRACT — this must run inside the SAME transaction as the handler it
    guards. Committing the claim separately would mean a handler that then failed
    left the event marked processed with nothing written, and Stripe's retry
    would be turned away by the claim: the change would be lost permanently.
    Sharing a transaction means a failed handler rolls the claim back too, and
    the retry reprocesses cleanly.
    """
    row = await conn.fetchrow(
        "INSERT INTO processed_stripe_events (event_id, event_type) "
        "VALUES ($1, $2) ON CONFLICT (event_id) DO NOTHING RETURNING event_id",
        event_id,
        event_type,
    )
    return row is not None


async def resolve_tenant_for_stripe_ids(
    conn: asyncpg.Connection,
    *,
    subscription_id: str | None,
    customer_id: str | None,
) -> uuid.UUID | None:
    """Find the tenant behind a Stripe subscription/customer, or None.

    The fallback for events that carry no ``tenant_id`` metadata — a subscription
    created directly in the Stripe Dashboard, for instance. The subscription id is
    tried first because it is the more specific of the two: one customer can
    accumulate several subscription rows over time, so matching on the customer
    alone is only meaningful once no subscription row matches.
    """
    if subscription_id:
        row = await conn.fetchrow(
            "SELECT tenant_id FROM subscriptions WHERE stripe_subscription_id = $1",
            subscription_id,
        )
        if row is not None:
            return uuid.UUID(str(row["tenant_id"]))
    if customer_id:
        row = await conn.fetchrow(
            "SELECT tenant_id FROM subscriptions WHERE stripe_customer_id = $1 "
            "ORDER BY created_at DESC LIMIT 1",
            customer_id,
        )
        if row is not None:
            return uuid.UUID(str(row["tenant_id"]))
    return None


async def get_stripe_customer_id(
    conn: asyncpg.Connection, tenant_id: uuid.UUID
) -> str | None:
    """The tenant's most recent Stripe Customer id, if it has ever had one.

    Used to reuse one billing identity across repeat checkouts, and to open the
    Billing Portal (which is addressed by customer, not by subscription).
    """
    row = await conn.fetchrow(
        "SELECT stripe_customer_id FROM subscriptions "
        "WHERE tenant_id = $1 AND stripe_customer_id IS NOT NULL "
        "ORDER BY created_at DESC LIMIT 1",
        tenant_id,
    )
    return str(row["stripe_customer_id"]) if row is not None else None


async def upsert_stripe_subscription(
    conn: asyncpg.Connection,
    *,
    tenant_id: uuid.UUID,
    tier: str,
    status: str,
    stripe_status: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    stripe_price_id: str,
    cancel_at_period_end: bool,
    query_limit_monthly: int | None,
    user_limit: int | None,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
    event_created_at: datetime,
) -> None:
    """Insert or update the row for one Stripe subscription.

    The conflict target is migration 011's PARTIAL unique index, so the
    ``WHERE stripe_subscription_id IS NOT NULL`` predicate below must stay
    byte-identical to the one in that migration — Postgres infers the index by
    matching the predicate, and a mismatch fails at runtime with "no unique or
    exclusion constraint matching the ON CONFLICT specification".

    The trailing ``WHERE`` on the DO UPDATE is the out-of-order guard. Stripe
    gives no ordering guarantee, so a stale ``customer.subscription.updated`` can
    arrive after a newer one; without this, a superseded downgrade could land on
    top of a current upgrade and silently cut a paying tenant's quota. Comparing
    the event's own ``created`` timestamp makes the row monotonic: it only ever
    moves forward.

    ``>=`` rather than ``>`` so that two events sharing a timestamp still apply
    (Stripe emits several events from one state change within the same second);
    the idempotency ledger already prevents the same event applying twice.

    NULL ``stripe_event_created_at`` means a row written before this guard
    existed, and always loses to an incoming event — so no backfill is needed.
    """
    await conn.execute(
        """
        INSERT INTO subscriptions (
            tenant_id, tier, status, stripe_status,
            stripe_customer_id, stripe_subscription_id, stripe_price_id,
            cancel_at_period_end, query_limit_monthly, user_limit,
            current_period_start, current_period_end, stripe_event_created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL
        DO UPDATE SET
            tenant_id               = EXCLUDED.tenant_id,
            tier                    = EXCLUDED.tier,
            status                  = EXCLUDED.status,
            stripe_status           = EXCLUDED.stripe_status,
            stripe_customer_id      = EXCLUDED.stripe_customer_id,
            stripe_price_id         = EXCLUDED.stripe_price_id,
            cancel_at_period_end    = EXCLUDED.cancel_at_period_end,
            query_limit_monthly     = EXCLUDED.query_limit_monthly,
            user_limit              = EXCLUDED.user_limit,
            current_period_start    = EXCLUDED.current_period_start,
            current_period_end      = EXCLUDED.current_period_end,
            stripe_event_created_at = EXCLUDED.stripe_event_created_at
        WHERE subscriptions.stripe_event_created_at IS NULL
           OR EXCLUDED.stripe_event_created_at >= subscriptions.stripe_event_created_at
        """,
        tenant_id,
        tier,
        status,
        stripe_status,
        stripe_customer_id,
        stripe_subscription_id,
        stripe_price_id,
        cancel_at_period_end,
        query_limit_monthly,
        user_limit,
        current_period_start,
        current_period_end,
        event_created_at,
    )
