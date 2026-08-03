"""Whether a stored subscription still entitles its tenant to service (#185).

``enforce_tier_limit`` (#25) originally read ``query_limit_monthly`` and ignored
``status`` entirely, which was harmless only because the ``subscriptions`` table
was empty. Once the #32 webhook began writing rows, a tenant whose subscription
went ``cancelled`` kept a row saying ``query_limit_monthly = 100`` and therefore
kept its full paid allowance indefinitely. This module is the missing step: it
turns a stored row into what the tenant is *currently* owed.

Pure functions over a ``SubscriptionRecord`` and a clock. No I/O, so every branch
below is directly testable without a database — which matters, because several of
them are reachable only at specific points in a two-week dunning cycle.

Three decisions are encoded here and are easy to get wrong in isolation:

  * **``cancel_at_period_end`` is not consulted.** A customer who cancels through
    the Billing Portal has paid for the period they are in and stays ``active``
    until it ends; Stripe only moves the status afterwards. Revoking early would
    be taking money for service not rendered.

  * **``past_due`` keeps its full quota, for a bounded time.** Stripe's dunning
    settings already encode "retry for N days, then give up", so re-implementing
    that schedule here would mean two timers that can disagree. Instead the raw
    Stripe status is trusted while it says retrying, and a backstop caps how long
    that can last — see ``_within_dunning_grace``.

  * **Anything unrecognised lapses.** This mirrors ``map_stripe_status`` in
    ``src.billing.events``: an unknown state should under-serve a customer
    visibly rather than over-serve one silently.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Final

from pydantic import BaseModel

from src.billing.plans import LAPSED_QUERY_LIMIT_MONTHLY
from src.db.subscriptions import SubscriptionRecord

#: Mapped statuses (migration 003's CHECK domain) that entitle outright.
#: ``trialing`` is included because a trial is a deliberate grant of service.
_ENTITLED_STATUSES: Final[frozenset[str]] = frozenset({"active", "trialing"})

#: Raw Stripe statuses meaning the retry schedule is over and Stripe has stopped
#: trying to collect. These map onto ``past_due`` like an in-progress retry does,
#: so without checking the raw value they would collect a second grace window on
#: top of the dunning they have already exhausted.
_DUNNING_EXHAUSTED: Final[frozenset[str]] = frozenset({"unpaid"})

#: Ceiling on how long a ``past_due`` subscription keeps its paid quota, measured
#: from the start of the period it has not paid for. Normally inert: Stripe
#: resolves the subscription one way or the other well inside this window. It
#: exists so that a dunning rule left on "do nothing after final retry" cannot
#: quietly grant a non-paying tenant its full allowance forever — the same
#: failure this module was written to close, arrived at by a different route.
PAST_DUE_GRACE_DAYS: Final = 14


class Entitlement(BaseModel, frozen=True):
    """What a tenant may actually use right now.

    ``query_limit_monthly`` follows the same convention as everywhere else in the
    billing code: ``None`` means unlimited. ``is_lapsed`` is not cosmetic — it
    selects the usage *window* as well as the message the caller returns, because
    a lapsed subscription's billing period is frozen at whenever it stopped being
    paid for and cannot be used to bound a monthly allowance.
    """

    query_limit_monthly: int | None
    is_lapsed: bool


#: No subscription row at all. Deliberately unlimited rather than lapsed: the
#: bootstrap ``system`` tenant (migration 008) has no row, and neither do any
#: tenants predating Stripe, so lapsing this case would lock existing users out
#: of production the moment it deployed. "Never had a subscription" and "had one
#: and lost it" are different situations and only the second is a revenue leak.
_UNLIMITED: Final = Entitlement(query_limit_monthly=None, is_lapsed=False)

_LAPSED: Final = Entitlement(
    query_limit_monthly=LAPSED_QUERY_LIMIT_MONTHLY, is_lapsed=True
)


def resolve_entitlement(
    sub: SubscriptionRecord | None,
    *,
    now: datetime | None = None,
    grace_days: int = PAST_DUE_GRACE_DAYS,
) -> Entitlement:
    """Reduce a stored subscription to the allowance it currently grants."""
    if sub is None:
        return _UNLIMITED
    if sub.status in _ENTITLED_STATUSES:
        return Entitlement(query_limit_monthly=sub.query_limit_monthly, is_lapsed=False)
    if sub.status == "past_due" and _within_dunning_grace(
        sub, now=now or datetime.now(UTC), grace_days=grace_days
    ):
        return Entitlement(query_limit_monthly=sub.query_limit_monthly, is_lapsed=False)
    return _LAPSED


def select_effective_subscription(
    subs: Sequence[SubscriptionRecord],
    *,
    now: datetime | None = None,
    grace_days: int = PAST_DUE_GRACE_DAYS,
) -> SubscriptionRecord | None:
    """Pick the row that decides access: any entitled one, else the first.

    Necessary because a tenant can hold several rows and "the newest" is not the
    same as "the one being paid for". The case that matters is a subscriber who
    starts a second checkout and abandons the 3-D Secure step: Stripe creates an
    ``incomplete`` subscription, the webhook stores it as ``cancelled``, and it is
    newer than the row they are actually paying on. Reading only the newest row
    would revoke a paying customer's access on the strength of a checkout they
    never completed.

    ``subs`` is expected newest-first among equally-entitled rows (which is what
    ``get_tenant_subscriptions`` returns), so the first entitled row is also the
    most recent one. Falling back to ``subs[0]`` when nothing is entitled keeps
    the lapsed decision on the most recent row rather than an ancient one.
    """
    for sub in subs:
        if not resolve_entitlement(sub, now=now, grace_days=grace_days).is_lapsed:
            return sub
    return subs[0] if subs else None


def _within_dunning_grace(
    sub: SubscriptionRecord, *, now: datetime, grace_days: int
) -> bool:
    """Is this ``past_due`` subscription still inside its retry window?

    ``current_period_start`` is the anchor because it is the one timestamp that
    does not move while dunning runs. The obvious alternative,
    ``stripe_event_created_at``, is bumped by each new event, so a subscription
    that emitted an update every few days would renew its own grace period
    indefinitely. ``current_period_end`` is no better — Stripe advances the period
    at renewal even when the invoice goes unpaid, so it would grant a full free
    month. The period the tenant has not paid for started at
    ``current_period_start``, and the grace runs from there.

    A missing anchor returns ``True``. Hand-provisioned enterprise rows (#35) have
    no billing period at all, and cutting off an invoiced customer because a
    nullable column is null would be a worse error than the one being prevented.
    """
    if sub.stripe_status in _DUNNING_EXHAUSTED:
        return False
    if sub.current_period_start is None:
        return True
    return now <= sub.current_period_start + timedelta(days=grace_days)
