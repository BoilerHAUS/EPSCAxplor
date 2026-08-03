"""Tests for src/routes/billing.py — Checkout, Portal, and the webhook (#32).

The webhook is the security boundary of the whole billing feature: it is the one
unauthenticated endpoint, and what it writes decides every tenant's quota. So the
signatures below are computed with real HMAC-SHA256 over the real
``{timestamp}.{payload}`` scheme rather than mocked away — a test that stubs out
``construct_event`` would pass just as happily against an endpoint with no
verification at all, which is precisely the free-upgrade vulnerability this
guards.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.auth.dependencies import CurrentUser, get_current_user
from src.config import Settings, get_settings
from src.main import app

WEBHOOK_SECRET = "whsec_test_secret"  # noqa: S105 — dummy, test mode only
TENANT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = dict(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="billing-route-secret",
        stripe_secret_key="sk_test_dummy",
        stripe_webhook_secret=WEBHOOK_SECRET,
        stripe_price_individual="price_ind_123",
        stripe_price_professional="price_pro_456",
        public_web_url="https://epscaxplor.com",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _sign(payload: str, secret: str = WEBHOOK_SECRET, *, age_seconds: int = 0) -> str:
    """Produce a genuine Stripe-Signature header for ``payload``."""
    timestamp = int(time.time()) - age_seconds
    signature = hmac.new(
        secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def _subscription_event(
    *, event_id: str = "evt_1", price_id: str = "price_ind_123", status: str = "active"
) -> str:
    return json.dumps(
        {
            "id": event_id,
            "object": "event",
            "type": "customer.subscription.created",
            "created": int(time.time()),
            "data": {
                "object": {
                    "id": "sub_abc",
                    "object": "subscription",
                    "customer": "cus_abc",
                    "status": status,
                    "cancel_at_period_end": False,
                    "metadata": {"tenant_id": str(TENANT_ID)},
                    "items": {
                        "data": [
                            {
                                "id": "si_1",
                                "price": {"id": price_id},
                                "current_period_start": 1785535200,
                                "current_period_end": 1788213600,
                            }
                        ]
                    },
                }
            },
        }
    )


@contextlib.contextmanager
def _billing_env(
    *,
    settings: Settings | None = None,
    claimed: bool = True,
    tenant_lookup: uuid.UUID | None = TENANT_ID,
) -> Iterator[dict[str, AsyncMock]]:
    """Patch the DB seam under the billing route.

    ``claimed`` False simulates an event id already present in
    ``processed_stripe_events`` — i.e. a Stripe retry of something we finished.
    """
    resolved = settings or _settings()
    mocks = {
        "claim": AsyncMock(return_value=claimed),
        "upsert": AsyncMock(return_value=None),
        "resolve_tenant": AsyncMock(return_value=tenant_lookup),
    }

    @contextlib.asynccontextmanager
    async def _fake_acquire(*_a: object, **_k: object) -> Any:
        conn = AsyncMock()

        @contextlib.asynccontextmanager
        async def _txn(*_ta: object, **_tk: object) -> Any:
            yield None

        conn.transaction = _txn
        yield conn

    app.dependency_overrides[get_settings] = lambda: resolved
    with patch("src.routes.billing.acquire", _fake_acquire), patch(
        "src.routes.billing.claim_stripe_event", mocks["claim"]
    ), patch("src.routes.billing.upsert_stripe_subscription", mocks["upsert"]), patch(
        "src.routes.billing.resolve_tenant_for_stripe_ids", mocks["resolve_tenant"]
    ):
        yield mocks
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


# ─── webhook: signature verification ─────────────────────────────────────────


def test_valid_signature_is_processed(client: TestClient) -> None:
    payload = _subscription_event()
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200
    mocks["upsert"].assert_awaited_once()


def test_invalid_signature_is_rejected_and_writes_nothing(client: TestClient) -> None:
    """The core free-upgrade guard."""
    payload = _subscription_event(price_id="price_pro_456")
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload, "whsec_wrong_secret")},
        )
    assert response.status_code == 400
    mocks["claim"].assert_not_awaited()
    mocks["upsert"].assert_not_awaited()


def test_missing_signature_header_is_rejected(client: TestClient) -> None:
    payload = _subscription_event()
    with _billing_env() as mocks:
        response = client.post("/billing/webhook", content=payload)
    assert response.status_code == 400
    mocks["upsert"].assert_not_awaited()


def test_garbage_signature_header_is_rejected(client: TestClient) -> None:
    payload = _subscription_event()
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": "t=abc,v1=nonsense"},
        )
    assert response.status_code == 400
    mocks["upsert"].assert_not_awaited()


def test_body_tampering_after_signing_is_rejected(client: TestClient) -> None:
    """Sign the individual plan, then swap the body to the professional plan."""
    signed_payload = _subscription_event(price_id="price_ind_123")
    tampered = _subscription_event(price_id="price_pro_456")
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=tampered,
            headers={"Stripe-Signature": _sign(signed_payload)},
        )
    assert response.status_code == 400
    mocks["upsert"].assert_not_awaited()


def test_stale_timestamp_is_rejected(client: TestClient) -> None:
    """A correctly-signed body replayed long afterwards is still refused.

    Stripe's default tolerance is 300s; this bounds capture-and-replay of a
    genuine event by an attacker who observed the body in transit.
    """
    payload = _subscription_event()
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload, age_seconds=3600)},
        )
    assert response.status_code == 400
    mocks["upsert"].assert_not_awaited()


def test_webhook_fails_closed_when_secret_is_unconfigured(client: TestClient) -> None:
    """No signing secret must mean 'accept nothing', never 'skip the check'."""
    payload = _subscription_event()
    unconfigured = _settings(stripe_webhook_secret=None)
    with _billing_env(settings=unconfigured) as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 503
    mocks["claim"].assert_not_awaited()
    mocks["upsert"].assert_not_awaited()


def test_webhook_needs_no_bearer_token(client: TestClient) -> None:
    """Stripe cannot present a JWT; the route must not require one."""
    payload = _subscription_event()
    with _billing_env():
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200


def test_oversized_body_is_refused_before_buffering(client: TestClient) -> None:
    """The webhook is the only unauthenticated, unrate-limited route, so it is
    the only one where an anonymous caller decides how much memory to allocate.
    A flood of huge bodies would otherwise exhaust the single API process and
    take /query and /auth down with it."""
    payload = "x" * (2 * 1024 * 1024)
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 413
    mocks["claim"].assert_not_awaited()
    mocks["upsert"].assert_not_awaited()


def test_a_normal_sized_event_is_unaffected_by_the_cap(client: TestClient) -> None:
    payload = _subscription_event()
    assert len(payload) < 1024 * 1024
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200
    mocks["upsert"].assert_awaited_once()


# ─── webhook: idempotency and replay ─────────────────────────────────────────


def test_replayed_event_is_acknowledged_but_not_reprocessed(client: TestClient) -> None:
    payload = _subscription_event()
    with _billing_env(claimed=False) as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200
    mocks["claim"].assert_awaited_once()
    mocks["upsert"].assert_not_awaited()


def test_unknown_event_type_is_acknowledged_without_writing(client: TestClient) -> None:
    """Unhandled types must return 2xx or Stripe retries them forever."""
    payload = json.dumps(
        {
            "id": "evt_ping",
            "object": "event",
            "type": "customer.discount.created",
            "created": int(time.time()),
            "data": {"object": {}},
        }
    )
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200
    mocks["upsert"].assert_not_awaited()


def test_subscription_on_an_unknown_price_is_not_granted_a_tier(
    client: TestClient,
) -> None:
    payload = _subscription_event(price_id="price_somebody_elses")
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200
    mocks["upsert"].assert_not_awaited()


def test_unresolvable_tenant_is_acknowledged_without_writing(client: TestClient) -> None:
    """No tenant metadata and no stored mapping — ack so Stripe stops retrying,
    but write nothing rather than guess which tenant to upgrade."""
    payload = json.dumps(
        {
            "id": "evt_orphan",
            "object": "event",
            "type": "customer.subscription.created",
            "created": int(time.time()),
            "data": {
                "object": {
                    "id": "sub_orphan",
                    "customer": "cus_orphan",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "metadata": {},
                    "items": {"data": [{"price": {"id": "price_ind_123"}}]},
                }
            },
        }
    )
    with _billing_env(tenant_lookup=None) as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200
    mocks["upsert"].assert_not_awaited()


def test_invoice_payment_failed_never_writes_a_subscription_row(
    client: TestClient,
) -> None:
    """Pin the invoice handler's read-only contract as an executable invariant.

    ``customer.subscription.updated`` (status=past_due) is emitted for the same
    failure and is the authoritative carrier of price and period. Writing a row
    from the invoice instead would race that event and persist a status without
    a verified tier — so this stays a log-only path, enforced here rather than
    only by a comment.
    """
    payload = json.dumps(
        {
            "id": "evt_invoice_failed",
            "object": "event",
            "type": "invoice.payment_failed",
            "created": int(time.time()),
            "data": {
                "object": {
                    "id": "in_1",
                    "customer": "cus_abc",
                    "parent": {
                        "type": "subscription_details",
                        "subscription_details": {"subscription": "sub_abc"},
                    },
                }
            },
        }
    )
    with _billing_env() as mocks:
        response = client.post(
            "/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _sign(payload)},
        )
    assert response.status_code == 200
    # Claimed (so a retry is a no-op) but deliberately never written.
    mocks["claim"].assert_awaited_once()
    mocks["upsert"].assert_not_awaited()


# ─── checkout + portal: authentication ───────────────────────────────────────


def test_checkout_session_requires_authentication(client: TestClient) -> None:
    with _billing_env():
        response = client.post("/billing/checkout-session", json={"tier": "individual"})
    assert response.status_code == 401


def test_portal_session_requires_authentication(client: TestClient) -> None:
    with _billing_env():
        response = client.post("/billing/portal-session")
    assert response.status_code == 401


@contextlib.contextmanager
def _as_tenant() -> Iterator[None]:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        tenant_id=TENANT_ID, user_id=uuid.uuid4()
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_checkout_rejects_enterprise_tier(client: TestClient) -> None:
    """Enterprise is manually invoiced (#35) and must not be self-serve."""
    with _billing_env(), _as_tenant():
        response = client.post("/billing/checkout-session", json={"tier": "enterprise"})
    assert response.status_code == 422


def test_checkout_rejects_unknown_tier(client: TestClient) -> None:
    with _billing_env(), _as_tenant():
        response = client.post("/billing/checkout-session", json={"tier": "platinum"})
    assert response.status_code == 422


def test_checkout_returns_503_when_stripe_unconfigured(client: TestClient) -> None:
    unconfigured = _settings(stripe_secret_key=None)
    with _billing_env(settings=unconfigured), _as_tenant():
        response = client.post("/billing/checkout-session", json={"tier": "individual"})
    assert response.status_code == 503


# ─── public plan catalog (consumed by #33) ───────────────────────────────────


def test_plans_endpoint_is_public_and_lists_configured_tiers(client: TestClient) -> None:
    """#33's pricing page must be able to render before login."""
    with _billing_env():
        response = client.get("/billing/plans")
    assert response.status_code == 200
    plans = response.json()["plans"]
    assert [p["tier"] for p in plans] == ["individual", "professional"]
    assert plans[0]["price_id"] == "price_ind_123"
    assert plans[0]["user_limit"] == 1


def test_plans_endpoint_is_empty_when_stripe_unconfigured(client: TestClient) -> None:
    with _billing_env(settings=_settings(stripe_price_individual=None,
                                         stripe_price_professional=None)):
        response = client.get("/billing/plans")
    assert response.status_code == 200
    assert response.json()["plans"] == []
