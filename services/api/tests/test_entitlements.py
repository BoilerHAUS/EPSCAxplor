"""Tests for src/billing/entitlements.py — does a stored row still entitle? (#185)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from src.billing.entitlements import (
    PAST_DUE_GRACE_DAYS,
    resolve_entitlement,
    select_effective_subscription,
)
from src.billing.plans import LAPSED_QUERY_LIMIT_MONTHLY
from src.db.subscriptions import SubscriptionRecord

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def _sub(**overrides: Any) -> SubscriptionRecord:
    base: dict[str, Any] = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tier="individual",
        status="active",
        stripe_status="active",
        cancel_at_period_end=False,
        query_limit_monthly=100,
        user_limit=1,
        current_period_start=NOW - timedelta(days=3),
        current_period_end=NOW + timedelta(days=27),
    )
    base.update(overrides)
    return SubscriptionRecord(**base)


# ─── entitled states ─────────────────────────────────────────────────────────


def test_no_subscription_is_unlimited() -> None:
    """The bootstrap tenant (migration 008) has no row and must not be locked out."""
    entitlement = resolve_entitlement(None, now=NOW)
    assert entitlement.query_limit_monthly is None
    assert entitlement.is_lapsed is False


def test_active_keeps_its_quota() -> None:
    entitlement = resolve_entitlement(_sub(query_limit_monthly=100), now=NOW)
    assert entitlement.query_limit_monthly == 100
    assert entitlement.is_lapsed is False


def test_trialing_keeps_its_quota() -> None:
    entitlement = resolve_entitlement(
        _sub(status="trialing", stripe_status="trialing"), now=NOW
    )
    assert entitlement.query_limit_monthly == 100
    assert entitlement.is_lapsed is False


def test_cancel_at_period_end_keeps_full_entitlement() -> None:
    """Migration 011's invariant: cancelling in the Portal does not revoke early.

    The subscription stays ``active`` and fully paid until the period actually
    ends, so a tenant who cancels on day 2 of a month keeps the whole month.
    """
    entitlement = resolve_entitlement(
        _sub(status="active", cancel_at_period_end=True, query_limit_monthly=1000),
        now=NOW,
    )
    assert entitlement.query_limit_monthly == 1000
    assert entitlement.is_lapsed is False


def test_active_enterprise_stays_unlimited() -> None:
    entitlement = resolve_entitlement(
        _sub(tier="enterprise", query_limit_monthly=None, stripe_status=None), now=NOW
    )
    assert entitlement.query_limit_monthly is None
    assert entitlement.is_lapsed is False


# ─── lapsed states ───────────────────────────────────────────────────────────


def test_cancelled_drops_to_the_lapsed_allowance() -> None:
    entitlement = resolve_entitlement(
        _sub(status="cancelled", stripe_status="canceled"), now=NOW
    )
    assert entitlement.query_limit_monthly == LAPSED_QUERY_LIMIT_MONTHLY
    assert entitlement.is_lapsed is True


def test_lapsed_enterprise_does_not_stay_unlimited() -> None:
    """A cancelled enterprise row carries query_limit_monthly = NULL.

    Passing that through would read as "unlimited" and hand a churned enterprise
    tenant permanent free service — the exact bug being fixed, in its worst form.
    """
    entitlement = resolve_entitlement(
        _sub(
            tier="enterprise",
            status="cancelled",
            stripe_status="canceled",
            query_limit_monthly=None,
        ),
        now=NOW,
    )
    assert entitlement.query_limit_monthly == LAPSED_QUERY_LIMIT_MONTHLY
    assert entitlement.is_lapsed is True


def test_unknown_status_fails_closed() -> None:
    """Mirrors map_stripe_status: an unrecognised state under-serves, not over-serves."""
    entitlement = resolve_entitlement(_sub(status="hibernating"), now=NOW)
    assert entitlement.is_lapsed is True


# ─── past_due: Stripe owns the grace window, the backstop bounds it ──────────


def test_past_due_within_grace_keeps_full_quota() -> None:
    """A failed charge must not cut off a customer while Stripe is still retrying."""
    entitlement = resolve_entitlement(
        _sub(
            status="past_due",
            stripe_status="past_due",
            current_period_start=NOW - timedelta(days=3),
        ),
        now=NOW,
    )
    assert entitlement.query_limit_monthly == 100
    assert entitlement.is_lapsed is False


def test_past_due_lapses_once_the_backstop_expires() -> None:
    """Bounds the damage if Stripe dunning is misconfigured to never terminate."""
    entitlement = resolve_entitlement(
        _sub(
            status="past_due",
            stripe_status="past_due",
            current_period_start=NOW - timedelta(days=PAST_DUE_GRACE_DAYS + 1),
        ),
        now=NOW,
    )
    assert entitlement.query_limit_monthly == LAPSED_QUERY_LIMIT_MONTHLY
    assert entitlement.is_lapsed is True


def test_backstop_boundary_is_inclusive() -> None:
    entitlement = resolve_entitlement(
        _sub(
            status="past_due",
            stripe_status="past_due",
            current_period_start=NOW - timedelta(days=PAST_DUE_GRACE_DAYS),
        ),
        now=NOW,
    )
    assert entitlement.is_lapsed is False


def test_unpaid_lapses_immediately_despite_a_fresh_period() -> None:
    """``unpaid`` means Stripe has finished retrying and given up.

    It maps onto ``past_due``, so without reading the raw status it would collect
    a second full grace window on top of the dunning it already exhausted.
    """
    entitlement = resolve_entitlement(
        _sub(
            status="past_due",
            stripe_status="unpaid",
            current_period_start=NOW - timedelta(days=1),
        ),
        now=NOW,
    )
    assert entitlement.query_limit_monthly == LAPSED_QUERY_LIMIT_MONTHLY
    assert entitlement.is_lapsed is True


def test_past_due_without_a_period_start_stays_entitled() -> None:
    """No anchor means the backstop cannot be measured, so it must not fire.

    Hand-provisioned rows (#35) have no billing period; failing closed here would
    cut off an invoiced enterprise customer on the strength of a missing column.
    """
    entitlement = resolve_entitlement(
        _sub(status="past_due", stripe_status="past_due", current_period_start=None),
        now=NOW,
    )
    assert entitlement.is_lapsed is False


# ─── choosing between several rows ───────────────────────────────────────────


def test_active_row_wins_over_a_newer_abandoned_checkout() -> None:
    """The regression that enforcing status would otherwise introduce.

    A subscriber who starts a second checkout and abandons 3-D Secure leaves an
    ``incomplete`` subscription, stored as ``cancelled`` and newer than the row
    they are actually paying on.
    """
    abandoned = _sub(status="cancelled", stripe_status="incomplete")
    paying = _sub(status="active", query_limit_monthly=1000)
    assert select_effective_subscription([abandoned, paying], now=NOW) is paying


def test_falls_back_to_the_first_row_when_all_are_lapsed() -> None:
    newest = _sub(status="cancelled", stripe_status="canceled")
    older = _sub(status="cancelled", stripe_status="canceled")
    assert select_effective_subscription([newest, older], now=NOW) is newest


def test_no_rows_selects_nothing() -> None:
    assert select_effective_subscription([], now=NOW) is None
