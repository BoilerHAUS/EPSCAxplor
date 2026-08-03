"""Outbound Stripe calls and the request shaping that precedes them (#32).

The parameter builders are pure and separate from the I/O so the rules that
matter — tax stays off until registration, the tenant id is stamped where the
webhook can find it, payment methods are never pinned — are asserted directly on
a dict instead of through a mocked SDK.

The Stripe client is constructed per call with an explicit key rather than by
assigning the module-global ``stripe.api_key``. That global is process-wide
mutable state: it would leak between tests, and in an async app it makes "which
key was in effect for this request" a function of scheduling order.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast

import stripe

from src.config import Settings

if TYPE_CHECKING:  # pragma: no cover — import-time cost avoided at runtime
    # Stripe declares its request TypedDicts under TYPE_CHECKING only, so they
    # exist for mypy but not at runtime. The builders below return plain dicts
    # (conditional keys are impractical to express as a TypedDict, and tests
    # assert on ordinary dicts), and are cast to these at the SDK call boundary.
    from stripe.params.billing_portal._session_create_params import (
        SessionCreateParams as PortalCreateParams,
    )
    from stripe.params.checkout._session_create_params import (
        SessionCreateParams as CheckoutCreateParams,
    )


class BillingError(RuntimeError):
    """A billing failure that should surface to the caller as 503.

    Base class so routes can catch this alongside ``stripe.StripeError`` and
    treat "we could not produce a usable Stripe session" uniformly, whatever the
    reason.
    """


class BillingNotConfiguredError(BillingError):
    """Raised when a Stripe call is attempted without the required settings."""


def billing_configured(settings: Settings) -> bool:
    """True when Checkout/Portal calls can be made at all."""
    return bool(settings.stripe_secret_key)


def _client(settings: Settings) -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise BillingNotConfiguredError("STRIPE_SECRET_KEY is not set")
    return stripe.StripeClient(settings.stripe_secret_key)


def build_checkout_params(
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    price_id: str,
    customer_id: str | None,
    customer_email: str | None,
) -> dict[str, Any]:
    """Build the Checkout Session request for a subscription purchase.

    ``payment_method_types`` is deliberately absent. Stripe's guidance is to omit
    it so eligible methods are resolved from Dashboard settings; pinning
    ``["card"]`` would exclude Canadian pre-authorized debit, which is the method
    most relevant to recurring Canadian B2B and a stated reason for choosing
    Stripe over a merchant of record.
    """
    tax_enabled = settings.stripe_automatic_tax_enabled
    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        # client_reference_id rides on the Session only.
        "client_reference_id": str(tenant_id),
        "metadata": {"tenant_id": str(tenant_id)},
        # ...so the tenant is ALSO stamped onto the Subscription itself. This is
        # the detail the whole webhook depends on: customer.subscription.* events
        # do not carry client_reference_id, and Stripe does not guarantee that
        # checkout.session.completed is delivered before them. Without this, a
        # subscription event can arrive with no way to identify its tenant.
        "subscription_data": {"metadata": {"tenant_id": str(tenant_id)}},
        "success_url": f"{_web_origin(settings)}/billing/success"
        "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": f"{_web_origin(settings)}/pricing",
        # Both tax features are gated together (#181): collecting a buyer's
        # GST/HST number serves no purpose while an unregistered small supplier
        # cannot charge tax. Passing enabled=False explicitly (rather than
        # omitting the key) keeps the intent visible in the request.
        "automatic_tax": {"enabled": tax_enabled},
        "tax_id_collection": {"enabled": tax_enabled},
    }

    if tax_enabled:
        # Stripe Tax needs an address to pick a jurisdiction. Requiring one while
        # tax is off would be checkout friction that buys nothing.
        params["billing_address_collection"] = "required"

    if customer_id:
        # Reusing the existing Customer keeps one billing identity per tenant.
        # Stripe rejects a request carrying both `customer` and `customer_email`.
        params["customer"] = customer_id
    elif customer_email:
        params["customer_email"] = customer_email

    return params


def build_portal_params(settings: Settings, *, customer_id: str) -> dict[str, Any]:
    """Build the Billing Portal session request (cancel, card, invoices)."""
    return {
        "customer": customer_id,
        "return_url": f"{_web_origin(settings)}/account",
    }


async def create_checkout_session(
    settings: Settings, params: dict[str, Any], *, idempotency_key: str
) -> str:
    """Create a Checkout Session and return its hosted URL.

    ``idempotency_key`` means a user double-clicking "Subscribe", or a retried
    request, reuses the same Session instead of creating a second one.
    """
    session = await _client(settings).v1.checkout.sessions.create_async(
        cast("CheckoutCreateParams", params),
        options={"idempotency_key": idempotency_key},
    )
    if not session.url:
        # Should not happen for a hosted Checkout Session, but the SDK types it
        # as optional and a None here would otherwise reach the client as a
        # response with a null redirect target.
        raise BillingError("Stripe returned a Checkout Session with no URL")
    return session.url


async def create_portal_session(settings: Settings, params: dict[str, Any]) -> str:
    """Create a Billing Portal session and return its hosted URL."""
    session = await _client(settings).v1.billing_portal.sessions.create_async(
        cast("PortalCreateParams", params)
    )
    return session.url


def _web_origin(settings: Settings) -> str:
    """The public web origin, without a trailing slash."""
    return settings.public_web_url.rstrip("/")
