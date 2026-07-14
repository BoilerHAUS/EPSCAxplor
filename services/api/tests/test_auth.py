"""Tests for src/auth/dependencies.py — JWT auth dependency + rate limiter (#23).

Replaces the interim shared-bearer-token tests (#85); that mechanism was removed.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.auth import CurrentUser, enforce_rate_limit, get_current_user
from src.auth.dependencies import _request_log
from src.auth.tokens import encode_access_token
from src.config import Settings, get_settings

JWT_SECRET = "dependency-test-secret"


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = dict(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret=JWT_SECRET,
    )
    base.update(overrides)
    return Settings(**base)


def _token(
    settings: Settings,
    *,
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    role: str = "member",
    expiry_seconds: int = 900,
) -> str:
    return encode_access_token(
        user_id=user_id or uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        role=role,
        secret=settings.jwt_secret,
        expiry_seconds=expiry_seconds,
    )


def _auth_app(settings: Settings) -> TestClient:
    """App whose route is guarded exactly like /query (rate limit off here)."""
    app = FastAPI()

    @app.get("/guarded")
    async def guarded(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:  # noqa: B008
        return {"tenant": str(user.tenant_id), "user": str(user.user_id)}

    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


class TestJwtDependency:
    def test_401_without_authorization_header(self) -> None:
        client = _auth_app(_settings())
        assert client.get("/guarded").status_code == 401

    def test_401_non_bearer_scheme(self) -> None:
        client = _auth_app(_settings())
        resp = client.get("/guarded", headers={"Authorization": "Basic Zm9vOmJhcg=="})
        assert resp.status_code == 401

    def test_401_empty_bearer(self) -> None:
        client = _auth_app(_settings())
        assert client.get("/guarded", headers={"Authorization": "Bearer "}).status_code == 401

    def test_401_garbage_token_sets_www_authenticate(self) -> None:
        client = _auth_app(_settings())
        resp = client.get("/guarded", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_401_expired_token(self) -> None:
        settings = _settings()
        client = _auth_app(settings)
        token = _token(settings, expiry_seconds=-1)
        resp = client.get("/guarded", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_401_token_signed_with_other_secret(self) -> None:
        settings = _settings()
        client = _auth_app(settings)
        token = _token(_settings(jwt_secret="a-totally-different-secret"))
        resp = client.get("/guarded", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_200_with_valid_token_exposes_claims(self) -> None:
        settings = _settings()
        client = _auth_app(settings)
        uid, tid = uuid.uuid4(), uuid.uuid4()
        token = _token(settings, user_id=uid, tenant_id=tid)
        resp = client.get("/guarded", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == {"tenant": str(tid), "user": str(uid)}

    def test_bearer_scheme_is_case_insensitive(self) -> None:
        settings = _settings()
        client = _auth_app(settings)
        token = _token(settings)
        resp = client.get("/guarded", headers={"Authorization": f"bearer {token}"})
        assert resp.status_code == 200


class TestRateLimit:
    def setup_method(self) -> None:
        _request_log.clear()

    @staticmethod
    def _rate_app(settings: Settings) -> TestClient:
        """Route guarded by the limiter alone (no auth) to isolate limiter behavior."""
        app = FastAPI()

        @app.get("/rl", dependencies=[Depends(enforce_rate_limit)])
        async def rl() -> dict[str, bool]:
            return {"ok": True}

        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    def test_disabled_when_zero(self) -> None:
        client = self._rate_app(_settings(query_rate_limit_per_minute=0))
        for _ in range(50):
            assert client.get("/rl").status_code == 200

    def test_429_above_limit(self) -> None:
        client = self._rate_app(_settings(query_rate_limit_per_minute=3))
        codes = [client.get("/rl").status_code for _ in range(5)]
        assert codes == [200, 200, 200, 429, 429]

    def test_separate_clients_have_separate_windows(self) -> None:
        client = self._rate_app(_settings(query_rate_limit_per_minute=2))
        a = {"X-Forwarded-For": "1.1.1.1"}
        b = {"X-Forwarded-For": "2.2.2.2"}
        assert [client.get("/rl", headers=a).status_code for _ in range(3)] == [200, 200, 429]
        assert client.get("/rl", headers=b).status_code == 200

    async def test_window_expiry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.auth.dependencies as dep

        settings = _settings(query_rate_limit_per_minute=1)

        class FakeRequest:
            headers: dict[str, str] = {}
            client = None

        clock = {"t": 1000.0}
        monkeypatch.setattr(dep.time, "monotonic", lambda: clock["t"])

        await enforce_rate_limit(FakeRequest(), settings)  # type: ignore[arg-type]
        with pytest.raises(HTTPException) as exc:
            await enforce_rate_limit(FakeRequest(), settings)  # type: ignore[arg-type]
        assert exc.value.status_code == 429

        clock["t"] += 61.0
        await enforce_rate_limit(FakeRequest(), settings)  # type: ignore[arg-type]
