"""Tests for src/billing/gateway.py — outbound Stripe request shaping (#32).

These assert on the parameter dicts before they reach Stripe, so the rules below
are checked without a network call or a mocked SDK.

The tax rules here intentionally CONTRADICT issue #32's task list, which
specifies ``automatic_tax.enabled = true`` and ``tax_id_collection.enabled =
true``. The owner is a Canadian small supplier under the CAD $30,000 threshold
and is not GST/HST registered: an unregistered supplier must not charge GST/HST,
and Stripe Tax bills 0.5% per transaction to compute a 0% rate. Both are
therefore gated behind ``STRIPE_AUTOMATIC_TAX_ENABLED`` and default to off. See
#181, which stays open as the registration tripwire.
"""

from __future__ import annotations

import uuid

from src.billing.gateway import build_checkout_params, build_portal_params
from src.config import Settings

TENANT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = dict(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="gateway-test-secret",
        stripe_secret_key="sk_test_dummy",
        stripe_price_individual="price_ind_123",
        stripe_price_professional="price_pro_456",
        public_web_url="https://epscaxplor.com",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


# ─── tax: the small-supplier constraint ──────────────────────────────────────


def test_automatic_tax_is_off_by_default() -> None:
    """An unregistered supplier must not charge GST/HST."""
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id=None, customer_email=None,
    )
    assert params["automatic_tax"] == {"enabled": False}


def test_tax_id_collection_is_off_by_default() -> None:
    """Collecting a buyer's GST/HST number is pointless while we cannot charge
    tax, and adds a checkout field that will confuse Canadian B2B buyers."""
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id=None, customer_email=None,
    )
    assert params["tax_id_collection"] == {"enabled": False}


def test_tax_flag_enables_both_tax_features_together() -> None:
    """Flipping the flag after GST/HST registration (#181) turns on collection
    and the buyer's tax-ID field in one move."""
    params = build_checkout_params(
        _settings(stripe_automatic_tax_enabled=True), tenant_id=TENANT_ID,
        price_id="price_ind_123", customer_id=None, customer_email=None,
    )
    assert params["automatic_tax"] == {"enabled": True}
    assert params["tax_id_collection"] == {"enabled": True}


def test_billing_address_is_only_required_once_tax_is_on() -> None:
    """Stripe Tax needs an address to determine jurisdiction; without tax the
    extra field is pure checkout friction."""
    without_tax = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id=None, customer_email=None,
    )
    with_tax = build_checkout_params(
        _settings(stripe_automatic_tax_enabled=True), tenant_id=TENANT_ID,
        price_id="price_ind_123", customer_id=None, customer_email=None,
    )
    assert "billing_address_collection" not in without_tax
    assert with_tax["billing_address_collection"] == "required"


# ─── Stripe's own guidance ───────────────────────────────────────────────────


def test_payment_method_types_is_never_pinned() -> None:
    """Per Stripe's billing guidance, omitting this lets the Dashboard's dynamic
    payment methods apply. Hardcoding ``["card"]`` would lock out Canadian
    pre-authorized debit — the method most relevant to recurring Canadian B2B.
    """
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id=None, customer_email=None,
    )
    assert "payment_method_types" not in params


def test_mode_is_subscription_with_a_single_line_item() -> None:
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_pro_456",
        customer_id=None, customer_email=None,
    )
    assert params["mode"] == "subscription"
    assert params["line_items"] == [{"price": "price_pro_456", "quantity": 1}]


# ─── tenant binding ──────────────────────────────────────────────────────────


def test_tenant_id_is_stamped_on_the_subscription_not_just_the_session() -> None:
    """The decisive detail for webhook correctness.

    ``client_reference_id`` rides on the Checkout Session only.
    ``customer.subscription.*`` events do not carry it, and Stripe does not
    guarantee that ``checkout.session.completed`` arrives first — so without
    ``subscription_data.metadata`` a subscription event can arrive with no way
    to tell which tenant it belongs to.
    """
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id=None, customer_email=None,
    )
    assert params["client_reference_id"] == str(TENANT_ID)
    assert params["subscription_data"]["metadata"]["tenant_id"] == str(TENANT_ID)


def test_existing_customer_is_reused_and_email_is_not_resent() -> None:
    """Passing both ``customer`` and ``customer_email`` is a Stripe API error."""
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id="cus_existing", customer_email="buyer@example.com",
    )
    assert params["customer"] == "cus_existing"
    assert "customer_email" not in params


def test_first_time_buyer_gets_email_prefilled() -> None:
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id=None, customer_email="buyer@example.com",
    )
    assert params["customer_email"] == "buyer@example.com"
    assert "customer" not in params


def test_urls_are_built_from_the_configured_web_origin() -> None:
    params = build_checkout_params(
        _settings(), tenant_id=TENANT_ID, price_id="price_ind_123",
        customer_id=None, customer_email=None,
    )
    assert params["success_url"].startswith("https://epscaxplor.com/")
    assert "{CHECKOUT_SESSION_ID}" in params["success_url"]
    assert params["cancel_url"].startswith("https://epscaxplor.com/")


def test_portal_params_bind_customer_and_return_url() -> None:
    params = build_portal_params(_settings(), customer_id="cus_abc")
    assert params["customer"] == "cus_abc"
    assert params["return_url"].startswith("https://epscaxplor.com/")
