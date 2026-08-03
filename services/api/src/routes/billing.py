"""Stripe subscription billing — Checkout, Portal, catalog, webhook (#32).

Populating ``subscriptions`` here is what switches tier enforcement on:
``enforce_tier_limit`` (#25) already reads that table and fails open until rows
exist, so no enforcement code changes as part of this feature.

**Auth shape.** Auth and rate limiting in this codebase are per-route
dependencies, not global middleware, so the webhook needs no exclusion list — it
simply declares neither. (Issue #32's warning about excluding it from JWT
middleware and per-IP rate limiting describes an architecture this app does not
have.) The webhook authenticates by Stripe signature instead, which is the only
credential Stripe can present.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Mapping
from typing import Annotated, Any, Literal, get_args

import asyncpg
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.auth import CurrentUser, get_current_user
from src.billing.events import (
    SUBSCRIPTION_EVENT_TYPES,
    SubscriptionSync,
    subscription_id_from_invoice,
    subscription_sync_from_event,
)
from src.billing.gateway import (
    BillingError,
    billing_configured,
    build_checkout_params,
    build_portal_params,
    create_checkout_session,
    create_portal_session,
)
from src.billing.plans import SELF_SERVE_TIERS, PublicPlan, price_id_for_tier, public_catalog
from src.config import Settings, get_settings
from src.db import acquire
from src.db.subscriptions import (
    claim_stripe_event,
    get_stripe_customer_id,
    resolve_tenant_for_stripe_ids,
    upsert_stripe_subscription,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

#: Invoice events are handled for their side effect on subscription status only.
_INVOICE_EVENT_TYPES = frozenset({"invoice.payment_failed"})

#: Hard ceiling on the webhook request body. See ``_read_bounded_body``.
_MAX_WEBHOOK_BODY_BYTES = 1024 * 1024


class CheckoutRequest(BaseModel):
    """The plan a tenant wants to buy.

    A closed ``Literal`` over self-serve tiers, so an unknown or non-self-serve
    value is a 422 from FastAPI's validation rather than something the handler
    has to defend against. Enterprise is absent deliberately: it is manually
    invoiced (#35), never bought through Checkout.

    Naming a tier is not the same as being granted one. This only selects which
    configured Price to send the customer to; the tier the tenant actually
    receives is derived server-side from the Price on the resulting Stripe
    subscription, in the webhook.
    """

    tier: Literal["individual", "professional"]


class SessionResponse(BaseModel):
    url: str


class PlansResponse(BaseModel):
    plans: list[PublicPlan]


@router.get("/plans", response_model=PlansResponse)
async def list_plans(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PlansResponse:
    """The purchasable plans, with their Price IDs and entitlements.

    Unauthenticated on purpose: #33's pricing page has to render before login.
    Nothing here is secret — a Price ID identifies a plan and grants nothing —
    and this is what keeps the price_id -> tier mapping in one place instead of
    duplicated into the web lane. Reads config only; no database or Stripe call.
    """
    return PlansResponse(plans=public_catalog(settings))


@router.post("/checkout-session", response_model=SessionResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    """Start a subscription: returns a hosted Stripe Checkout URL to redirect to."""
    if not billing_configured(settings):
        raise _billing_unavailable()

    price_id = price_id_for_tier(settings, payload.tier)
    if price_id is None:
        # The tier is valid but this environment has no Price configured for it.
        logger.error("no Stripe price configured for tier %s", payload.tier)
        raise _billing_unavailable()

    async with acquire() as conn:
        customer_id = await get_stripe_customer_id(conn, current_user.tenant_id)

    params = build_checkout_params(
        settings,
        tenant_id=current_user.tenant_id,
        price_id=price_id,
        customer_id=customer_id,
        customer_email=None,
    )
    try:
        # Scoped to tenant+price so a double-clicked "Subscribe" reuses one
        # Session, while a genuine later purchase of a different plan is not
        # collapsed into the earlier one.
        url = await create_checkout_session(
            settings,
            params,
            idempotency_key=f"checkout:{current_user.tenant_id}:{price_id}",
        )
    except (stripe.StripeError, BillingError):
        logger.exception("Stripe checkout session creation failed")
        raise _billing_unavailable() from None
    return SessionResponse(url=url)


@router.post("/portal-session", response_model=SessionResponse)
async def create_portal(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    """Open the Billing Portal — cancel, change card, download invoices."""
    if not billing_configured(settings):
        raise _billing_unavailable()

    async with acquire() as conn:
        customer_id = await get_stripe_customer_id(conn, current_user.tenant_id)
    if customer_id is None:
        raise HTTPException(
            status_code=409,
            detail="No billing account for this tenant; start a subscription first.",
        )

    try:
        url = await create_portal_session(
            settings, build_portal_params(settings, customer_id=customer_id)
        )
    except (stripe.StripeError, BillingError):
        logger.exception("Stripe portal session creation failed")
        raise _billing_unavailable() from None
    return SessionResponse(url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, bool]:
    """Sync subscription state from Stripe.

    Deliberately declares no ``get_current_user`` and no ``enforce_rate_limit``
    dependency: Stripe cannot present a JWT, and it retries in bursts that a
    per-IP limiter would drop. The signature check below is the authentication.

    Returns 2xx for anything it cannot act on (unknown event type, unrecognised
    price, unresolvable tenant) so Stripe stops retrying an event that will never
    succeed. Genuine failures are left to raise, so Stripe retries those.
    """
    secret = settings.stripe_webhook_secret
    if not secret:
        # Fail CLOSED. A missing signing secret must mean "accept nothing", never
        # "skip verification" — the latter would make every tenant's tier
        # writable by an unauthenticated caller.
        logger.error("STRIPE_WEBHOOK_SECRET is not set; rejecting webhook delivery")
        raise _billing_unavailable()

    # The RAW body, before any parsing. The signature covers these exact bytes,
    # so verifying a re-serialised dict would compare against different bytes and
    # fail (or, worse, pass against something other than what was signed).
    raw_body = await _read_bounded_body(request)
    signature = request.headers.get("stripe-signature")
    try:
        # Untyped in the SDK; the ignore is on the call, not on the result.
        stripe.Webhook.construct_event(raw_body, signature, secret)  # type: ignore[no-untyped-call]
        # Re-parse the SAME verified bytes into plain dicts. `construct_event`
        # returns a StripeObject, which in stripe 15.x is neither a dict nor a
        # Mapping: it has no `.get()` (attribute access is proxied to field
        # lookup and raises AttributeError), and its recursive-to-dict helper is
        # private. Parsing the verified payload ourselves keeps src/billing/events
        # working on ordinary dicts, off any private SDK surface. The bytes parsed
        # here are byte-for-byte the ones just verified, so this adds no trust gap.
        event: dict[str, Any] = json.loads(raw_body)
    except (ValueError, stripe.SignatureVerificationError):
        # Covers a malformed body, a missing/garbled header, a wrong secret, and
        # a timestamp outside Stripe's default 300s tolerance (its replay bound).
        # 400, with no detail — an attacker probing the endpoint learns nothing
        # about which part failed.
        logger.warning("rejected Stripe webhook with an invalid signature")
        raise HTTPException(status_code=400, detail="invalid signature") from None

    # ── everything below here is verified-authentic Stripe data ──────────────
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="invalid event")
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    if not event_id:
        raise HTTPException(status_code=400, detail="invalid event")

    if event_type not in SUBSCRIPTION_EVENT_TYPES | _INVOICE_EVENT_TYPES:
        # Endpoints often receive more types than they subscribe to. Ack quietly.
        return {"received": True}

    async with acquire() as conn:
        # One transaction spanning the claim AND the write. If the handler fails,
        # the claim rolls back with it and Stripe's retry reprocesses; committing
        # the claim first would strand the event as "processed but never applied".
        async with conn.transaction():
            if not await claim_stripe_event(conn, event_id, event_type):
                logger.info("skipping already-processed Stripe event %s", event_id)
                return {"received": True}
            await _apply_event(conn, settings, event)

    return {"received": True}


async def _apply_event(
    conn: asyncpg.Connection, settings: Settings, event: Mapping[str, Any]
) -> None:
    """Route a verified event to its handler. Runs inside the claim transaction."""
    if event.get("type") in _INVOICE_EVENT_TYPES:
        _log_invoice_failure(event)
        # No write. Stripe also emits customer.subscription.updated with
        # status=past_due for the same failure, and THAT event carries the price
        # and period this row needs. Deriving a subscription row from the invoice
        # instead would mean writing a status without a verified tier.
        return

    sync = subscription_sync_from_event(settings, event)
    if sync is None:
        # Unrecognised price, or a shape we cannot read. Never grant a tier on it.
        logger.warning(
            "ignoring subscription event %s: no known plan matched", event.get("id")
        )
        return

    tenant_id = sync.tenant_id or await resolve_tenant_for_stripe_ids(
        conn,
        subscription_id=sync.stripe_subscription_id,
        customer_id=sync.stripe_customer_id,
    )
    if tenant_id is None:
        # A subscription created outside the app with no metadata and no prior
        # row. Acknowledge, but write nothing — guessing which tenant to upgrade
        # is worse than leaving it for an operator.
        logger.error(
            "cannot resolve tenant for Stripe subscription %s (customer %s)",
            sync.stripe_subscription_id,
            sync.stripe_customer_id,
        )
        return

    await _write_sync(conn, tenant_id, sync)


async def _write_sync(
    conn: asyncpg.Connection, tenant_id: uuid.UUID, sync: SubscriptionSync
) -> None:
    await upsert_stripe_subscription(
        conn,
        tenant_id=tenant_id,
        tier=sync.tier,
        status=sync.status,
        stripe_status=sync.stripe_status,
        stripe_customer_id=sync.stripe_customer_id,
        stripe_subscription_id=sync.stripe_subscription_id,
        stripe_price_id=sync.stripe_price_id,
        cancel_at_period_end=sync.cancel_at_period_end,
        query_limit_monthly=sync.query_limit_monthly,
        user_limit=sync.user_limit,
        current_period_start=sync.current_period_start,
        current_period_end=sync.current_period_end,
        event_created_at=sync.event_created_at,
    )


def _log_invoice_failure(event: Mapping[str, Any]) -> None:
    invoice = (event.get("data") or {}).get("object") or {}
    logger.warning(
        "Stripe invoice payment failed for subscription %s",
        subscription_id_from_invoice(invoice),
    )


async def _read_bounded_body(request: Request) -> bytes:
    """Read the request body, refusing anything implausibly large.

    ``/billing/webhook`` is the one route with no authentication and no rate
    limit, so it is the one route where an unauthenticated caller controls how
    many bytes the process buffers. Reading first and validating afterwards would
    let a flood of large-bodied POSTs exhaust memory before the signature check
    ever runs — and because the API is a single process, that would take
    ``/query`` and ``/auth`` down with it.

    A real Stripe event is a few KB; their documented ceiling is well under this
    limit, so a body over 1 MiB is not a payload we would ever act on.

    ``Content-Length`` is checked first to reject the common case without reading
    anything, then the stream is counted as it arrives — a chunked request can
    omit or understate the header, so the declared length alone is not a bound.
    """
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > _MAX_WEBHOOK_BODY_BYTES:
                raise _payload_too_large()
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid request") from None

    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > _MAX_WEBHOOK_BODY_BYTES:
            raise _payload_too_large()
        chunks.append(chunk)
    return b"".join(chunks)


def _payload_too_large() -> HTTPException:
    return HTTPException(status_code=413, detail="payload too large")


def _billing_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Billing is not available.")


def _assert_checkout_tiers_match_catalog() -> None:
    """Fail at import if ``CheckoutRequest`` and the plan catalog disagree.

    ``CheckoutRequest.tier`` has to be a literal for FastAPI to validate it, so
    it restates what ``SELF_SERVE_TIERS`` already says. Adding a tier to the
    catalog and forgetting the literal would otherwise surface as a customer
    getting a 422 on a plan the pricing page is advertising. A plain ``assert``
    would be stripped under ``python -O``, hence the explicit raise.
    """
    literal_tiers = set(get_args(CheckoutRequest.model_fields["tier"].annotation))
    if literal_tiers != set(SELF_SERVE_TIERS):
        raise RuntimeError(
            f"CheckoutRequest tiers {sorted(literal_tiers)} do not match "
            f"SELF_SERVE_TIERS {sorted(SELF_SERVE_TIERS)}"
        )


_assert_checkout_tiers_match_catalog()
