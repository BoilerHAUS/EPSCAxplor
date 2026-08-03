"""The subscription plan catalog — price IDs, tiers, and entitlements (#32).

This module is the single source of truth for *what a tenant gets*, and it is
shared on purpose. #33 (pricing page + checkout redirect) consumes the same
catalog over ``GET /billing/plans`` rather than re-listing Stripe Price IDs in
the web lane, so a price can never drift between the two.

The split between what lives here and what lives in ``Settings`` is deliberate:

- **Price IDs are configuration.** Stripe issues different ids in test and live
  mode, so they must come from the environment.
- **Entitlements are product definition.** The quota attached to "professional"
  is the same in every environment, so it lives here as code, where it is
  reviewable and diffable, instead of becoming four more env vars that could be
  set inconsistently between dev and prod.

Security note: ``tier_for_price_id`` is the function that decides a paying
tenant's quota, and it is reached from the webhook — i.e. from data that
originates outside the system. It is written as a closed lookup over configured,
non-empty price IDs so that neither an unknown price nor a missing one can
resolve to a paid tier.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel

from src.config import Settings

TIER_INDIVIDUAL: Final = "individual"
TIER_PROFESSIONAL: Final = "professional"
TIER_ENTERPRISE: Final = "enterprise"

#: Tiers a customer can buy without talking to a human. Enterprise is excluded
#: by design (#35): it is provisioned manually with negotiated terms — PO
#: number / net-30 invoicing or Canadian pre-authorized debit — so it has no
#: self-serve Price and must be rejected by the checkout route.
SELF_SERVE_TIERS: Final[tuple[str, ...]] = (TIER_INDIVIDUAL, TIER_PROFESSIONAL)


class PlanEntitlements(BaseModel, frozen=True):
    """What a tier grants. ``None`` means unlimited.

    ``None`` is not a placeholder — it is the value ``enforce_tier_limit`` reads
    to short-circuit, and the NULL that migration 003 documents as "unlimited
    (enterprise)". Writing 0 here would lock enterprise out entirely.
    """

    query_limit_monthly: int | None
    user_limit: int | None


#: Seat counts mirror docs/planning.md §Subscription Tiers: individual is a
#: single user, professional is up to 10, enterprise is unlimited. Query quotas
#: are not specified there; these are the launch values and are the one number to
#: revisit once real usage data exists.
_ENTITLEMENTS: Final[dict[str, PlanEntitlements]] = {
    TIER_INDIVIDUAL: PlanEntitlements(query_limit_monthly=100, user_limit=1),
    TIER_PROFESSIONAL: PlanEntitlements(query_limit_monthly=1000, user_limit=10),
    TIER_ENTERPRISE: PlanEntitlements(query_limit_monthly=None, user_limit=None),
}

#: What a tenant keeps once its subscription has definitively lapsed — cancelled,
#: or past_due past the point where Stripe has stopped retrying (#185).
#:
#: This is deliberately NOT a fourth tier. Migration 003's CHECK constraint allows
#: only individual/professional/enterprise, and a lapsed tenant's row keeps the
#: tier it was bought on; this is the allowance applied *instead of* that tier's
#: quota once ``src.billing.entitlements`` judges the row unentitled. Keeping it
#: out of the catalog means it has no Price, cannot be checked out, and never
#: appears on the pricing page — it is a lapsed state, not a product.
#:
#: Small but non-zero on purpose: it keeps a churned account able to spot-check an
#: agreement (and to see that the product still works) without leaving a paid
#: allowance running for free. Every one of these queries still costs a Claude
#: call, so this is the number to watch if abandoned accounts accumulate.
LAPSED_QUERY_LIMIT_MONTHLY: Final = 10


class PublicPlan(BaseModel, frozen=True):
    """A self-serve plan as exposed to the web layer.

    ``price_id`` is safe to publish: it identifies a Price, grants nothing on its
    own, and is visible in any Stripe Checkout URL. Publishing it is what lets
    #33 render a pricing page without a second copy of the mapping.
    """

    tier: str
    price_id: str
    query_limit_monthly: int | None
    user_limit: int | None


def entitlements_for_tier(tier: str) -> PlanEntitlements:
    """Return the entitlements for ``tier``, raising ``KeyError`` if undefined.

    Raising is intentional. Every caller reaches this with a tier that came from
    ``tier_for_price_id`` (i.e. already validated against the catalog), so an
    unknown tier means the catalog and the caller have gone out of sync — a bug
    that should surface as a 500 and a retried webhook, not as a silently
    invented quota.
    """
    return _ENTITLEMENTS[tier]


def price_id_for_tier(settings: Settings, tier: str) -> str | None:
    """Return the configured Stripe Price ID for a self-serve tier.

    ``None`` when the tier is not self-serve (enterprise) or its price is unset.
    """
    configured = _configured_prices(settings)
    return configured.get(tier)


def tier_for_price_id(settings: Settings, price_id: str | None) -> str | None:
    """Map a Stripe Price ID back to the tier it sells. ``None`` if unrecognised.

    This is the server-side derivation that #32 requires: the tier a tenant
    receives is decided here, from the price Stripe says the subscription is on,
    and never from anything the client sent.

    A falsy ``price_id`` returns ``None`` before any comparison. That guard is
    load-bearing rather than defensive tidiness: an unset config slot is also
    ``None``, so a direct ``price_id == settings.stripe_price_professional``
    comparison would match ``None == None`` and hand out the professional tier to
    a subscription that carries no price at all.
    """
    if not price_id:
        return None
    for tier, configured_price in _configured_prices(settings).items():
        if configured_price == price_id:
            return tier
    return None


def public_catalog(settings: Settings) -> list[PublicPlan]:
    """The self-serve plans that are actually purchasable right now.

    Only configured tiers are listed, so a half-configured environment advertises
    nothing it cannot sell — a plan whose price is unset would otherwise render
    on the pricing page and fail at checkout.
    """
    return [
        PublicPlan(
            tier=tier,
            price_id=price_id,
            query_limit_monthly=_ENTITLEMENTS[tier].query_limit_monthly,
            user_limit=_ENTITLEMENTS[tier].user_limit,
        )
        for tier, price_id in _configured_prices(settings).items()
    ]


def _configured_prices(settings: Settings) -> dict[str, str]:
    """Self-serve tier -> Price ID, omitting any tier whose price is unset.

    Ordered cheapest-first so the pricing page and the catalog endpoint present
    tiers in a stable, sensible order without the web layer having to sort.
    """
    candidates = (
        (TIER_INDIVIDUAL, settings.stripe_price_individual),
        (TIER_PROFESSIONAL, settings.stripe_price_professional),
    )
    return {tier: price for tier, price in candidates if price}
