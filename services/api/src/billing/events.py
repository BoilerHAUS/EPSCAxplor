"""Stripe webhook payload -> subscription state (#32).

Pure functions over an event that has ALREADY passed signature verification.
Nothing here re-checks authenticity; ``src/routes/billing.py`` must not call into
this module until ``stripe.Webhook.construct_event`` has succeeded.

Two fields moved between Stripe API versions, and both are handled in either
shape here. This is not speculative future-proofing: a webhook body is serialised
with the API version pinned on the *webhook endpoint* in the Stripe Dashboard,
which is set when the endpoint is created and does NOT track the version the
installed SDK pins. A prod endpoint created a year ago and a freshly installed
SDK routinely disagree.

  * ``current_period_start`` / ``current_period_end`` moved off the Subscription
    onto each subscription ITEM in 2025-03-31.basil. Reading only the top level
    against a current endpoint yields ``None``, which silently degrades
    ``enforce_tier_limit`` from the real billing window to a calendar month.
  * ``invoice.subscription`` became
    ``invoice.parent.subscription_details.subscription``.

Issue #32's task list was written against the older shape of both.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final

from pydantic import BaseModel

from src.billing.plans import entitlements_for_tier, tier_for_price_id
from src.config import Settings

#: Event types that carry a full subscription snapshot.
SUBSCRIPTION_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
)

_DELETED_EVENT: Final = "customer.subscription.deleted"

#: Stripe's subscription statuses mapped onto the four values migration 003's
#: CHECK constraint allows. Anything not listed falls through to ``cancelled``.
#:
#: The vocabularies genuinely differ — Stripe writes ``canceled`` (one L) and has
#: four statuses 003 has no member for — so this mapping is required, not
#: cosmetic. The raw value is stored alongside in ``stripe_status`` so nothing is
#: lost and this table can be revised without a migration.
_STATUS_MAP: Final[dict[str, str]] = {
    "active": "active",
    "trialing": "trialing",
    "past_due": "past_due",
    # No successful payment for the current period. Not entitled, and Stripe will
    # move it on to canceled/unpaid on its own schedule.
    "unpaid": "past_due",
    "canceled": "cancelled",
    # `incomplete` means the FIRST payment never completed (Stripe gives it ~23h
    # before expiring it). Treating it as entitled would hand out a free period to
    # anyone who starts a checkout and abandons the 3-D Secure step.
    "incomplete": "cancelled",
    "incomplete_expired": "cancelled",
    "paused": "cancelled",
}


class SubscriptionSync(BaseModel, frozen=True):
    """The subscription state a webhook event asks us to persist.

    ``tenant_id`` is optional because a subscription created directly in the
    Stripe Dashboard carries no ``tenant_id`` metadata. The mapper reports that
    honestly instead of guessing; the route resolves it from the stored
    customer/subscription ids, and writes nothing if that also fails.
    """

    tenant_id: uuid.UUID | None
    tier: str
    status: str
    stripe_status: str
    stripe_customer_id: str
    stripe_subscription_id: str
    stripe_price_id: str
    cancel_at_period_end: bool
    query_limit_monthly: int | None
    user_limit: int | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    event_created_at: datetime


def map_stripe_status(stripe_status: str) -> str:
    """Map a Stripe subscription status onto migration 003's allowed values.

    Unknown statuses fail CLOSED to ``cancelled``. Stripe has added statuses
    before (``paused`` arrived after this schema was designed); defaulting an
    unrecognised one to ``active`` would grant service on a state we do not
    understand, whereas defaulting to ``cancelled`` at worst under-serves a
    paying customer visibly rather than over-serving one silently.
    """
    return _STATUS_MAP.get(stripe_status, "cancelled")


def subscription_sync_from_event(
    settings: Settings, event: Mapping[str, Any]
) -> SubscriptionSync | None:
    """Derive the state to persist, or ``None`` if the event is not actionable.

    Returns ``None`` — meaning "acknowledge and write nothing" — when the event
    is of an unrelated type, or when the subscription sits on a Price this
    deployment does not sell. That second case matters: an unrecognised price
    must never be granted a tier, and a 200 (rather than an error) stops Stripe
    retrying an event we will never be able to act on.
    """
    event_type = event.get("type")
    if event_type not in SUBSCRIPTION_EVENT_TYPES:
        return None

    subscription = (event.get("data") or {}).get("object") or {}
    price_id = _price_id_from_subscription(subscription)
    tier = tier_for_price_id(settings, price_id)
    if tier is None or price_id is None:
        return None

    subscription_id = subscription.get("id")
    customer_id = _id_of(subscription.get("customer"))
    if not subscription_id or not customer_id:
        return None

    # `deleted` is authoritative regardless of the status inside its own
    # snapshot: the object no longer exists, so the tenant is not entitled even
    # if the payload still reads "active".
    raw_status = str(subscription.get("status") or "canceled")
    status = "cancelled" if event_type == _DELETED_EVENT else map_stripe_status(raw_status)

    period_start, period_end = _period_from_subscription(subscription)
    entitlements = entitlements_for_tier(tier)

    return SubscriptionSync(
        tenant_id=_tenant_id_from_metadata(subscription.get("metadata")),
        tier=tier,
        status=status,
        stripe_status=raw_status,
        stripe_customer_id=customer_id,
        stripe_subscription_id=str(subscription_id),
        stripe_price_id=price_id,
        cancel_at_period_end=bool(subscription.get("cancel_at_period_end")),
        query_limit_monthly=entitlements.query_limit_monthly,
        user_limit=entitlements.user_limit,
        current_period_start=period_start,
        current_period_end=period_end,
        event_created_at=_timestamp(event.get("created")) or datetime.now(UTC),
    )


def subscription_id_from_invoice(invoice: Mapping[str, Any]) -> str | None:
    """Extract the subscription id an invoice belongs to, in either API shape.

    ``None`` for a one-off invoice with no subscription behind it.
    """
    legacy = _id_of(invoice.get("subscription"))
    if legacy:
        return legacy
    parent = invoice.get("parent") or {}
    details = parent.get("subscription_details") or {}
    return _id_of(details.get("subscription"))


def _price_id_from_subscription(subscription: Mapping[str, Any]) -> str | None:
    """The Price the subscription bills on.

    Only the first item is read. Every plan sold here is a single fixed-price
    line item, so a multi-item subscription is not something this deployment can
    create — and quietly picking one item's price out of several would be a worse
    outcome than the ``None`` that follows from an unrecognised shape.
    """
    items = (subscription.get("items") or {}).get("data") or []
    if not items:
        return None
    price = items[0].get("price") or {}
    return _id_of(price)


def _period_from_subscription(
    subscription: Mapping[str, Any],
) -> tuple[datetime | None, datetime | None]:
    """Read the current billing window from whichever shape the payload uses.

    Top level first (older endpoint versions), then the first subscription item
    (2025-03-31.basil onward). A ``None`` result is not fatal —
    ``enforce_tier_limit`` falls back to a calendar month — but it makes the
    quota window wrong, so both shapes are read rather than assuming one.
    """
    start = _timestamp(subscription.get("current_period_start"))
    end = _timestamp(subscription.get("current_period_end"))
    if start is not None or end is not None:
        return start, end

    items = (subscription.get("items") or {}).get("data") or []
    if not items:
        return None, None
    item = items[0]
    return (
        _timestamp(item.get("current_period_start")),
        _timestamp(item.get("current_period_end")),
    )


def _tenant_id_from_metadata(metadata: Mapping[str, Any] | None) -> uuid.UUID | None:
    """Parse ``metadata.tenant_id``, tolerating absence and malformed values.

    Metadata is free-form and writable from the Stripe Dashboard, so a bad value
    is a plausible operator error rather than an impossible state. Returning
    ``None`` routes it to the same DB-backed fallback as a missing value, instead
    of raising and pinning the webhook into a permanent retry loop.
    """
    if not metadata:
        return None
    raw = metadata.get("tenant_id")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def _id_of(value: Any) -> str | None:
    """Normalise a Stripe reference that may be a bare id or an expanded object."""
    if isinstance(value, str):
        return value or None
    if isinstance(value, Mapping):
        nested = value.get("id")
        return str(nested) if nested else None
    return None


def _timestamp(value: Any) -> datetime | None:
    """Convert a Stripe Unix timestamp to an aware UTC datetime."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return None
    return datetime.fromtimestamp(value, tz=UTC)
