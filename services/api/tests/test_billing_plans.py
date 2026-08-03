"""Tests for src/billing/plans.py — the shared plan catalog (#32).

This module is the single source of truth for the price_id -> tier mapping. It is
deliberately NOT private to the billing route: #33 (pricing page + checkout
redirect) consumes the same catalog through ``GET /billing/plans`` so a Stripe
Price ID is never duplicated into the web lane.

The security-critical property under test is that ``tier_for_price_id`` is a
CLOSED mapping over configured prices only. Tier is what decides a tenant's
quota, so anything that lets an unconfigured or absent price resolve to a paid
tier is a free-upgrade bug.
"""

from __future__ import annotations

import pytest

from src.billing.plans import (
    SELF_SERVE_TIERS,
    TIER_ENTERPRISE,
    TIER_INDIVIDUAL,
    TIER_PROFESSIONAL,
    entitlements_for_tier,
    price_id_for_tier,
    public_catalog,
    tier_for_price_id,
)
from src.config import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = dict(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="plans-test-secret",
        stripe_price_individual="price_ind_123",
        stripe_price_professional="price_pro_456",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


# ─── price_id -> tier (the free-upgrade surface) ─────────────────────────────


def test_configured_price_ids_map_to_their_tiers() -> None:
    settings = _settings()
    assert tier_for_price_id(settings, "price_ind_123") == TIER_INDIVIDUAL
    assert tier_for_price_id(settings, "price_pro_456") == TIER_PROFESSIONAL


def test_unknown_price_id_maps_to_nothing() -> None:
    """An unrecognised price must never resolve to a paid tier."""
    assert tier_for_price_id(_settings(), "price_attacker_supplied") is None


@pytest.mark.parametrize("bogus", ["", None])
def test_empty_or_missing_price_id_maps_to_nothing(bogus: str | None) -> None:
    """A subscription with no price must not silently match an unset config slot.

    This is the sharp edge: if ``stripe_price_professional`` is unset (None) and
    the lookup compared ``price_id == settings.stripe_price_professional``, then
    a payload with a missing price would match None == None and grant the
    professional tier for free.
    """
    assert tier_for_price_id(_settings(), bogus) is None  # type: ignore[arg-type]


def test_unconfigured_tier_slot_never_matches() -> None:
    """With professional unconfigured, nothing may resolve to professional."""
    settings = _settings(stripe_price_professional=None)
    assert tier_for_price_id(settings, "price_ind_123") == TIER_INDIVIDUAL
    assert tier_for_price_id(settings, "price_pro_456") is None
    assert tier_for_price_id(settings, None) is None  # type: ignore[arg-type]


def test_price_id_for_tier_round_trips() -> None:
    settings = _settings()
    for tier in SELF_SERVE_TIERS:
        price_id = price_id_for_tier(settings, tier)
        assert price_id is not None
        assert tier_for_price_id(settings, price_id) == tier


def test_enterprise_has_no_self_serve_price() -> None:
    """Enterprise is manually invoiced (#35), never bought through Checkout."""
    assert TIER_ENTERPRISE not in SELF_SERVE_TIERS
    assert price_id_for_tier(_settings(), TIER_ENTERPRISE) is None


# ─── entitlements ────────────────────────────────────────────────────────────


def test_entitlements_match_the_documented_tiers() -> None:
    """Individual = 1 seat, Professional = 10 seats, Enterprise = unlimited.

    Mirrors docs/planning.md §Subscription Tiers. NULL/None means unlimited and
    is what makes ``enforce_tier_limit`` fall through for enterprise.
    """
    assert entitlements_for_tier(TIER_INDIVIDUAL).user_limit == 1
    assert entitlements_for_tier(TIER_PROFESSIONAL).user_limit == 10
    assert entitlements_for_tier(TIER_ENTERPRISE).user_limit is None
    assert entitlements_for_tier(TIER_ENTERPRISE).query_limit_monthly is None


def test_paid_tiers_have_a_finite_query_quota() -> None:
    for tier in SELF_SERVE_TIERS:
        limit = entitlements_for_tier(tier).query_limit_monthly
        assert limit is not None and limit > 0


def test_professional_is_strictly_more_generous_than_individual() -> None:
    ind = entitlements_for_tier(TIER_INDIVIDUAL)
    pro = entitlements_for_tier(TIER_PROFESSIONAL)
    assert pro.query_limit_monthly is not None and ind.query_limit_monthly is not None
    assert pro.query_limit_monthly > ind.query_limit_monthly
    assert pro.user_limit is not None and ind.user_limit is not None
    assert pro.user_limit > ind.user_limit


def test_entitlements_for_unknown_tier_raises() -> None:
    """Fail loudly rather than inventing a quota for a tier we do not define."""
    with pytest.raises(KeyError):
        entitlements_for_tier("platinum")


# ─── public catalog (what #33 consumes) ──────────────────────────────────────


def test_public_catalog_lists_configured_self_serve_plans() -> None:
    catalog = public_catalog(_settings())
    assert [p.tier for p in catalog] == [TIER_INDIVIDUAL, TIER_PROFESSIONAL]
    assert [p.price_id for p in catalog] == ["price_ind_123", "price_pro_456"]
    assert catalog[0].user_limit == 1
    assert catalog[1].query_limit_monthly == entitlements_for_tier(
        TIER_PROFESSIONAL
    ).query_limit_monthly


def test_public_catalog_omits_unconfigured_plans() -> None:
    """Never advertise a plan whose price is unset — checkout would 500."""
    catalog = public_catalog(_settings(stripe_price_professional=None))
    assert [p.tier for p in catalog] == [TIER_INDIVIDUAL]


def test_public_catalog_is_empty_when_stripe_unconfigured() -> None:
    catalog = public_catalog(
        _settings(stripe_price_individual=None, stripe_price_professional=None)
    )
    assert catalog == []


def test_public_catalog_never_includes_enterprise() -> None:
    assert all(p.tier != TIER_ENTERPRISE for p in public_catalog(_settings()))
