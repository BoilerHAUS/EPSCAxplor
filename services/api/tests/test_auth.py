"""Tests for the interim /query protection (#85): bearer token + rate limit."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.auth import (
    SYSTEM_TENANT_ID,
    _request_log,
    enforce_rate_limit,
    get_current_user,
)
from src.config import Settings, get_settings


def _settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="test-jwt-secret",  # noqa: S106
    )
    base.update(overrides)
    return Settings(**base)


def _make_app(settings: Settings) -> TestClient:
    """App with a route guarded exactly like the query route."""
    from fastapi import Depends

    app = FastAPI()

    @app.get("/guarded", dependencies=[Depends(enforce_rate_limit)])
    async def guarded(user=Depends(get_current_user)):  # noqa: B008 — FastAPI idiom
        return {"tenant": str(user.tenant_id)}

    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


class TestBearerToken:
    def test_open_when_token_unset(self) -> None:
        client = _make_app(_settings(query_api_token=None, query_rate_limit_per_minute=0))
        resp = client.get("/guarded")
        assert resp.status_code == 200
        assert resp.json()["tenant"] == str(SYSTEM_TENANT_ID)

    def test_401_without_token(self) -> None:
        client = _make_app(
            _settings(query_api_token="sekrit", query_rate_limit_per_minute=0)  # noqa: S106
        )
        assert client.get("/guarded").status_code == 401

    def test_401_with_wrong_token(self) -> None:
        client = _make_app(
            _settings(query_api_token="sekrit", query_rate_limit_per_minute=0)  # noqa: S106
        )
        resp = client.get("/guarded", headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_200_with_correct_token(self) -> None:
        client = _make_app(
            _settings(query_api_token="sekrit", query_rate_limit_per_minute=0)  # noqa: S106
        )
        resp = client.get("/guarded", headers={"Authorization": "Bearer sekrit"})
        assert resp.status_code == 200

    def test_bearer_scheme_case_insensitive(self) -> None:
        client = _make_app(
            _settings(query_api_token="sekrit", query_rate_limit_per_minute=0)  # noqa: S106
        )
        resp = client.get("/guarded", headers={"Authorization": "bearer sekrit"})
        assert resp.status_code == 200


class TestRateLimit:
    def setup_method(self) -> None:
        _request_log.clear()

    def test_disabled_when_zero(self) -> None:
        client = _make_app(_settings(query_rate_limit_per_minute=0))
        for _ in range(50):
            assert client.get("/guarded").status_code == 200

    def test_429_above_limit(self) -> None:
        client = _make_app(_settings(query_rate_limit_per_minute=3))
        codes = [client.get("/guarded").status_code for _ in range(5)]
        assert codes == [200, 200, 200, 429, 429]

    def test_separate_clients_have_separate_windows(self) -> None:
        client = _make_app(_settings(query_rate_limit_per_minute=2))
        a = {"X-Forwarded-For": "1.1.1.1"}
        b = {"X-Forwarded-For": "2.2.2.2"}
        assert [client.get("/guarded", headers=a).status_code for _ in range(3)] == [200, 200, 429]
        assert client.get("/guarded", headers=b).status_code == 200

    @pytest.mark.asyncio
    async def test_window_expiry(self, monkeypatch) -> None:
        import src.auth as auth_mod

        settings = _settings(query_rate_limit_per_minute=1)

        class FakeRequest:
            headers: dict = {}
            client = None

        clock = {"t": 1000.0}
        monkeypatch.setattr(auth_mod.time, "monotonic", lambda: clock["t"])

        await enforce_rate_limit(FakeRequest(), settings)  # type: ignore[arg-type]
        with pytest.raises(HTTPException) as exc:
            await enforce_rate_limit(FakeRequest(), settings)  # type: ignore[arg-type]
        assert exc.value.status_code == 429

        clock["t"] += 61.0
        await enforce_rate_limit(FakeRequest(), settings)  # type: ignore[arg-type]
