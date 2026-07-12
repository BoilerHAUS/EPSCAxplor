"""Tests for src/routes/auth.py — login, refresh, logout (#23)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.auth.service import AuthError, TokenPair
from src.config import Settings, get_settings
from src.routes.auth import router as auth_router

COOKIE = "epsca_refresh"


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
    assert "SameSite=lax" in set_cookie


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
