"""Tests for src/routes/auth.py — login, refresh, logout (#23)."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.auth.dependencies import _auth_limiter, _request_log
from src.auth.service import AuthError, TokenPair
from src.config import Settings, get_settings
from src.routes.auth import LoginRequest
from src.routes.auth import router as auth_router

COOKIE = "epsca_refresh"


@pytest.fixture(autouse=True)
def _reset_limiters() -> Generator[None, None, None]:
    """The auth/query limiters are process-global module state; reset between
    tests so throttling counters do not leak across cases."""
    _auth_limiter._buckets.clear()
    _request_log.clear()
    yield
    _auth_limiter._buckets.clear()
    _request_log.clear()


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = dict(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="route-test-secret",
        refresh_cookie_secure=False,  # TestClient speaks http; keep the cookie
    )
    base.update(overrides)
    return Settings(**base)


def _client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(auth_router)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


# ─── login ────────────────────────────────────────────────────────────────────


def test_login_success_returns_token_and_sets_httponly_cookie() -> None:
    pair = TokenPair(access_token="access.jwt", refresh_token="raw-refresh-1", expires_in=900)
    client = _client(_settings())
    with patch("src.routes.auth.login", new=AsyncMock(return_value=pair)):
        resp = client.post("/auth/login", json={"email": "a@b.c", "password": "secret"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "access.jwt"
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900

    set_cookie = resp.headers["set-cookie"]
    assert f"{COOKIE}=raw-refresh-1" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/auth" in set_cookie
    assert "SameSite=strict" in set_cookie


def test_login_bad_credentials_returns_401_without_cookie() -> None:
    client = _client(_settings())
    with patch("src.routes.auth.login", new=AsyncMock(side_effect=AuthError("invalid credentials"))):
        resp = client.post("/auth/login", json={"email": "a@b.c", "password": "wrong"})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "unauthorized"
    assert "set-cookie" not in resp.headers


def test_login_rejects_malformed_body() -> None:
    client = _client(_settings())
    resp = client.post("/auth/login", json={"email": "a@b.c"})  # missing password
    assert resp.status_code == 422


def test_login_request_normalizes_email_at_boundary() -> None:
    """The API boundary lowercases + strips the email so login is case-insensitive (#141)."""
    assert LoginRequest(email="  You@X.COM ", password="pw").email == "you@x.com"


def test_login_request_rejects_whitespace_only_email() -> None:
    """A padded string that passes raw min_length must fail once normalized (#141)."""
    with pytest.raises(ValidationError):
        LoginRequest(email="   ", password="pw")


# ─── refresh ──────────────────────────────────────────────────────────────────


def test_refresh_rotates_cookie_and_returns_new_access_token() -> None:
    new_pair = TokenPair(access_token="access.jwt.2", refresh_token="raw-refresh-2", expires_in=900)
    client = _client(_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock(return_value=new_pair)):
        resp = client.post("/auth/refresh")

    assert resp.status_code == 200
    assert resp.json()["access_token"] == "access.jwt.2"
    assert f"{COOKIE}=raw-refresh-2" in resp.headers["set-cookie"]


def test_refresh_without_cookie_returns_401() -> None:
    client = _client(_settings())
    resp = client.post("/auth/refresh")
    assert resp.status_code == 401


def test_refresh_reuse_returns_401_and_clears_cookie() -> None:
    client = _client(_settings())
    client.cookies.set(COOKIE, "spent-token")
    with patch(
        "src.routes.auth.rotate_refresh_token",
        new=AsyncMock(side_effect=AuthError("refresh token reuse detected")),
    ):
        resp = client.post("/auth/refresh")

    assert resp.status_code == 401
    set_cookie = resp.headers.get("set-cookie", "").lower()
    assert COOKIE.lower() in set_cookie
    assert "max-age=0" in set_cookie or 'expires=thu, 01 jan 1970' in set_cookie


# ─── logout ───────────────────────────────────────────────────────────────────


def test_logout_revokes_family_and_clears_cookie() -> None:
    client = _client(_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.revoke_refresh_token", new=AsyncMock()) as revoke:
        resp = client.post("/auth/logout")

    assert resp.status_code == 204
    revoke.assert_awaited_once()
    assert "max-age=0" in resp.headers.get("set-cookie", "").lower()


def test_logout_without_cookie_is_noop_204() -> None:
    client = _client(_settings())
    with patch("src.routes.auth.revoke_refresh_token", new=AsyncMock()) as revoke:
        resp = client.post("/auth/logout")

    assert resp.status_code == 204
    revoke.assert_not_awaited()


# ─── CSRF origin guard on cookie-authenticated routes (#104) ─────────────────

WEB_ORIGIN = "https://epscaxplor.boilerhaus.org"


def _csrf_settings() -> Settings:
    return _settings(cors_origins=WEB_ORIGIN)


def test_refresh_with_cross_site_origin_returns_403_without_rotation() -> None:
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock()) as rotate:
        resp = client.post("/auth/refresh", headers={"Origin": "https://evil.example"})

    assert resp.status_code == 403
    rotate.assert_not_awaited()


def test_logout_with_cross_site_origin_returns_403_without_revocation() -> None:
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.revoke_refresh_token", new=AsyncMock()) as revoke:
        resp = client.post("/auth/logout", headers={"Origin": "https://evil.example"})

    assert resp.status_code == 403
    revoke.assert_not_awaited()


def test_refresh_with_allowed_origin_succeeds() -> None:
    pair = TokenPair(access_token="a.2", refresh_token="raw-2", expires_in=900)
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock(return_value=pair)):
        resp = client.post("/auth/refresh", headers={"Origin": WEB_ORIGIN})

    assert resp.status_code == 200


def test_logout_with_allowed_origin_succeeds() -> None:
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.revoke_refresh_token", new=AsyncMock()) as revoke:
        resp = client.post("/auth/logout", headers={"Origin": WEB_ORIGIN})

    assert resp.status_code == 204
    revoke.assert_awaited_once()


def test_allowed_origin_matching_ignores_case_and_trailing_slash() -> None:
    pair = TokenPair(access_token="a.2", refresh_token="raw-2", expires_in=900)
    client = _client(_settings(cors_origins=f"{WEB_ORIGIN}/"))
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock(return_value=pair)):
        resp = client.post(
            "/auth/refresh", headers={"Origin": "HTTPS://EPSCAxplor.BoilerHAUS.org"}
        )

    assert resp.status_code == 200


def test_same_host_origin_succeeds_even_if_not_in_cors_list() -> None:
    # Swagger UI / any same-origin caller: Origin equals the API's own host.
    pair = TokenPair(access_token="a.2", refresh_token="raw-2", expires_in=900)
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock(return_value=pair)):
        resp = client.post(
            "/auth/refresh",
            headers={"Origin": "http://testserver", "Host": "testserver"},
        )

    assert resp.status_code == 200


def test_null_origin_returns_403() -> None:
    # Sandboxed iframes / some redirect chains send the literal string "null";
    # treat it as cross-site.
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock()) as rotate:
        resp = client.post("/auth/refresh", headers={"Origin": "null"})

    assert resp.status_code == 403
    rotate.assert_not_awaited()


def test_cross_site_fetch_metadata_without_origin_returns_403() -> None:
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock()) as rotate:
        resp = client.post("/auth/refresh", headers={"Sec-Fetch-Site": "cross-site"})

    assert resp.status_code == 403
    rotate.assert_not_awaited()


def test_same_site_fetch_metadata_without_origin_succeeds() -> None:
    pair = TokenPair(access_token="a.2", refresh_token="raw-2", expires_in=900)
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock(return_value=pair)):
        resp = client.post("/auth/refresh", headers={"Sec-Fetch-Site": "same-site"})

    assert resp.status_code == 200


def test_non_browser_client_without_origin_headers_still_works() -> None:
    # curl / server-to-server clients send neither Origin nor Sec-Fetch-Site;
    # they cannot carry a victim's cookie, so they pass the guard.
    pair = TokenPair(access_token="a.2", refresh_token="raw-2", expires_in=900)
    client = _client(_csrf_settings())
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock(return_value=pair)):
        resp = client.post("/auth/refresh")

    assert resp.status_code == 200


def test_login_is_not_origin_guarded() -> None:
    # Login is credentialed by the request body, not the cookie — out of #104's
    # scope, and guarding it would break nothing-to-protect flows.
    pair = TokenPair(access_token="a.1", refresh_token="raw-1", expires_in=900)
    client = _client(_csrf_settings())
    with patch("src.routes.auth.login", new=AsyncMock(return_value=pair)):
        resp = client.post(
            "/auth/login",
            json={"email": "a@b.c", "password": "secret"},
            headers={"Origin": "https://evil.example"},
        )

    assert resp.status_code == 200


def test_refresh_cookie_defaults_to_samesite_strict() -> None:
    pair = TokenPair(access_token="a.1", refresh_token="raw-1", expires_in=900)
    client = _client(_settings())
    with patch("src.routes.auth.login", new=AsyncMock(return_value=pair)):
        resp = client.post("/auth/login", json={"email": "a@b.c", "password": "secret"})

    assert "SameSite=strict" in resp.headers["set-cookie"]


# ─── auth throttling (#140) ─────────────────────────────────────────────────

_LOGIN_BODY = {"email": "a@b.c", "password": "secret"}


def test_login_throttled_after_limit() -> None:
    # Failed logins must be counted (the limiter runs before the credential
    # check), so an online brute-force is capped: 3 attempts pass to the
    # handler (→ 401), the 4th and 5th are rejected with 429.
    client = _client(_settings(auth_rate_limit_per_minute=3))
    with patch(
        "src.routes.auth.login", new=AsyncMock(side_effect=AuthError("invalid credentials"))
    ):
        codes = [client.post("/auth/login", json=_LOGIN_BODY).status_code for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]


def test_login_throttle_429_carries_retry_after() -> None:
    client = _client(_settings(auth_rate_limit_per_minute=1))
    with patch(
        "src.routes.auth.login", new=AsyncMock(side_effect=AuthError("invalid credentials"))
    ):
        client.post("/auth/login", json=_LOGIN_BODY)  # consume the single slot
        resp = client.post("/auth/login", json=_LOGIN_BODY)
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") == "60"


def test_login_throttle_counts_successes_and_failures_in_one_bucket() -> None:
    # A success followed by failures share the same per-client bucket.
    pair = TokenPair(access_token="a.1", refresh_token="raw-1", expires_in=900)
    client = _client(_settings(auth_rate_limit_per_minute=2))
    with patch("src.routes.auth.login", new=AsyncMock(return_value=pair)):
        first = client.post("/auth/login", json=_LOGIN_BODY).status_code
    with patch(
        "src.routes.auth.login", new=AsyncMock(side_effect=AuthError("invalid credentials"))
    ):
        second = client.post("/auth/login", json=_LOGIN_BODY).status_code
        third = client.post("/auth/login", json=_LOGIN_BODY).status_code
    assert (first, second, third) == (200, 401, 429)


def test_auth_limit_disabled_when_zero() -> None:
    client = _client(_settings(auth_rate_limit_per_minute=0))
    with patch(
        "src.routes.auth.login", new=AsyncMock(side_effect=AuthError("invalid credentials"))
    ):
        codes = [client.post("/auth/login", json=_LOGIN_BODY).status_code for _ in range(10)]
    assert codes == [401] * 10


def test_refresh_throttled_after_limit() -> None:
    pair = TokenPair(access_token="a.2", refresh_token="raw-2", expires_in=900)
    client = _client(_settings(cors_origins=WEB_ORIGIN, auth_rate_limit_per_minute=2))
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock(return_value=pair)):
        codes = [
            client.post("/auth/refresh", headers={"Origin": WEB_ORIGIN}).status_code
            for _ in range(3)
        ]
    assert codes == [200, 200, 429]


def test_auth_throttle_precedes_csrf_on_refresh() -> None:
    # Ordering lock: the rate limiter runs before the CSRF-origin guard. A
    # cross-site request still consumes a slot (→ 403 the first time), and once
    # over the limit the throttle fires first (429 before the 403).
    client = _client(_settings(cors_origins=WEB_ORIGIN, auth_rate_limit_per_minute=1))
    client.cookies.set(COOKIE, "raw-refresh-1")
    with patch("src.routes.auth.rotate_refresh_token", new=AsyncMock()) as rotate:
        codes = [
            client.post("/auth/refresh", headers={"Origin": "https://evil.example"}).status_code
            for _ in range(2)
        ]
    assert codes == [403, 429]
    rotate.assert_not_awaited()
