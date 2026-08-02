"""Tests for src/billing/events.py — Stripe event -> subscription state (#32).

These are pure functions over an already-signature-verified event payload, so
they can be exercised without Stripe or Postgres.

Two payload shapes are tested throughout, deliberately. The webhook body is
serialised with the API version pinned on the *webhook endpoint* in the Stripe
Dashboard, which is NOT necessarily the version the installed SDK pins. Two
fields moved between those versions and both are load-bearing here:

  * ``current_period_start`` / ``current_period_end`` left the Subscription
    object and now live on each subscription ITEM (2025-03-31.basil onward).
    Reading only the top level yields None, which silently degrades
    ``enforce_tier_limit`` to a calendar-month window instead of the real
    billing period.
  * ``invoice.subscription`` was replaced by
    ``invoice.parent.subscription_details.subscription``.

Issue #32's task list was written against the older shape, so the "legacy"
cases below are the ones the issue describes and the "current" cases are what
today's API actually sends.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from src.billing.events import (
    map_stripe_status,
    subscription_id_from_invoice,
    subscription_sync_from_event,
)
from src.billing.plans import TIER_INDIVIDUAL, TIER_PROFESSIONAL
from src.config import Settings

TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

# 2026-08-01T10:00:00Z / 2026-09-01T10:00:00Z
PERIOD_START = 1785535200
PERIOD_END = 1788213600
EVENT_CREATED = 1785538800


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = dict(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="events-test-secret",
        stripe_price_individual="price_ind_123",
        stripe_price_professional="price_pro_456",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _subscription(
    *,
    price_id: str = "price_ind_123",
    status: str = "active",
    tenant_id: str | None = str(TENANT_ID),
    cancel_at_period_end: bool = False,
    legacy_period: bool = False,
) -> dict[str, Any]:
    """Build a Stripe Subscription payload in the current or legacy shape."""
    item: dict[str, Any] = {"id": "si_1", "price": {"id": price_id}}
    sub: dict[str, Any] = {
        "id": "sub_abc",
        "object": "subscription",
        "customer": "cus_abc",
        "status": status,
        "cancel_at_period_end": cancel_at_period_end,
        "metadata": {} if tenant_id is None else {"tenant_id": tenant_id},
        "items": {"object": "list", "data": [item]},
    }
    if legacy_period:
        sub["current_period_start"] = PERIOD_START
        sub["current_period_end"] = PERIOD_END
    else:
        item["current_period_start"] = PERIOD_START
        item["current_period_end"] = PERIOD_END
    return sub


def _event(obj: dict[str, Any], event_type: str, created: int = EVENT_CREATED) -> dict[str, Any]:
    return {
        "id": "evt_test_1",
        "object": "event",
        "type": event_type,
        "created": created,
        "data": {"object": obj},
    }


# ─── status mapping ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("stripe_status", "expected"),
    [
        ("active", "active"),
        ("trialing", "trialing"),
        ("past_due", "past_due"),
        ("unpaid", "past_due"),
        ("canceled", "cancelled"),  # Stripe spells it with one L, the DB with two
        ("incomplete", "cancelled"),
        ("incomplete_expired", "cancelled"),
        ("paused", "cancelled"),
    ],
)
def test_stripe_status_maps_into_the_db_check_constraint(
    stripe_status: str, expected: str
) -> None:
    """Every Stripe status must land on one of 003's four allowed values.

    Anything else raises a CHECK constraint violation at write time, which would
    surface as a 500 and an endlessly retried webhook.
    """
    assert map_stripe_status(stripe_status) == expected
    assert expected in {"active", "cancelled", "past_due", "trialing"}


def test_unknown_stripe_status_fails_closed() -> None:
    """A status Stripe adds later must not be treated as entitled."""
    assert map_stripe_status("some_future_status") == "cancelled"


# ─── subscription events ─────────────────────────────────────────────────────


@pytest.mark.parametrize("legacy_period", [False, True], ids=["current-api", "legacy-api"])
def test_subscription_created_yields_full_state(legacy_period: bool) -> None:
    event = _event(
        _subscription(legacy_period=legacy_period), "customer.subscription.created"
    )
    sync = subscription_sync_from_event(_settings(), event)

    assert sync is not None
    assert sync.tenant_id == TENANT_ID
    assert sync.tier == TIER_INDIVIDUAL
    assert sync.status == "active"
    assert sync.stripe_status == "active"
    assert sync.stripe_customer_id == "cus_abc"
    assert sync.stripe_subscription_id == "sub_abc"
    assert sync.stripe_price_id == "price_ind_123"
    assert sync.cancel_at_period_end is False
    assert sync.event_created_at == datetime.fromtimestamp(EVENT_CREATED, tz=UTC)


@pytest.mark.parametrize("legacy_period", [False, True], ids=["current-api", "legacy-api"])
def test_billing_period_is_read_from_either_payload_shape(legacy_period: bool) -> None:
    """The period window drives the tier-limit usage count — it must not be None."""
    event = _event(
        _subscription(legacy_period=legacy_period), "customer.subscription.updated"
    )
    sync = subscription_sync_from_event(_settings(), event)

    assert sync is not None
    assert sync.current_period_start == datetime.fromtimestamp(PERIOD_START, tz=UTC)
    assert sync.current_period_end == datetime.fromtimestamp(PERIOD_END, tz=UTC)


def test_tier_follows_the_price_not_any_client_input() -> None:
    event = _event(
        _subscription(price_id="price_pro_456"), "customer.subscription.updated"
    )
    sync = subscription_sync_from_event(_settings(), event)
    assert sync is not None
    assert sync.tier == TIER_PROFESSIONAL
    assert sync.query_limit_monthly == 1000
    assert sync.user_limit == 10


def test_unrecognised_price_is_rejected_outright() -> None:
    """A subscription on a price we do not sell must not be granted any tier."""
    event = _event(
        _subscription(price_id="price_not_ours"), "customer.subscription.created"
    )
    assert subscription_sync_from_event(_settings(), event) is None


def test_subscription_deleted_is_cancelled() -> None:
    event = _event(
        _subscription(status="canceled"), "customer.subscription.deleted"
    )
    sync = subscription_sync_from_event(_settings(), event)
    assert sync is not None
    assert sync.status == "cancelled"
    assert sync.stripe_status == "canceled"


def test_deleted_event_is_cancelled_even_if_payload_still_says_active() -> None:
    """``customer.subscription.deleted`` is authoritative regardless of the
    status field in its own snapshot — the object is gone."""
    event = _event(_subscription(status="active"), "customer.subscription.deleted")
    sync = subscription_sync_from_event(_settings(), event)
    assert sync is not None
    assert sync.status == "cancelled"


def test_cancel_at_period_end_is_carried_but_stays_entitled() -> None:
    """A portal cancellation keeps the tenant fully active until period end."""
    event = _event(
        _subscription(cancel_at_period_end=True), "customer.subscription.updated"
    )
    sync = subscription_sync_from_event(_settings(), event)
    assert sync is not None
    assert sync.cancel_at_period_end is True
    assert sync.status == "active"
    assert sync.query_limit_monthly == 100


def test_missing_tenant_metadata_leaves_tenant_unresolved() -> None:
    """A subscription created straight from the Dashboard carries no tenant_id.

    The pure mapper reports None rather than guessing; the route falls back to
    resolving the tenant from the stored customer/subscription id.
    """
    event = _event(_subscription(tenant_id=None), "customer.subscription.created")
    sync = subscription_sync_from_event(_settings(), event)
    assert sync is not None
    assert sync.tenant_id is None


def test_malformed_tenant_metadata_is_ignored_not_fatal() -> None:
    event = _event(_subscription(tenant_id="not-a-uuid"), "customer.subscription.created")
    sync = subscription_sync_from_event(_settings(), event)
    assert sync is not None
    assert sync.tenant_id is None


def test_unrelated_event_type_is_ignored() -> None:
    assert subscription_sync_from_event(_settings(), _event({}, "ping")) is None


# ─── invoice.payment_failed ──────────────────────────────────────────────────


def test_subscription_id_from_invoice_current_shape() -> None:
    invoice = {
        "id": "in_1",
        "customer": "cus_abc",
        "parent": {
            "type": "subscription_details",
            "subscription_details": {"subscription": "sub_abc"},
        },
    }
    assert subscription_id_from_invoice(invoice) == "sub_abc"


def test_subscription_id_from_invoice_legacy_shape() -> None:
    """The shape issue #32 was written against."""
    assert subscription_id_from_invoice({"id": "in_1", "subscription": "sub_abc"}) == "sub_abc"


def test_subscription_id_from_invoice_handles_expanded_object() -> None:
    """When the field is expanded it is an object, not a bare id string."""
    invoice = {
        "parent": {"subscription_details": {"subscription": {"id": "sub_abc"}}},
    }
    assert subscription_id_from_invoice(invoice) == "sub_abc"


def test_one_off_invoice_has_no_subscription() -> None:
    assert subscription_id_from_invoice({"id": "in_1", "parent": None}) is None
    assert subscription_id_from_invoice({"id": "in_1"}) is None
