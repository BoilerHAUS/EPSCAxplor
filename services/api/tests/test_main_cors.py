"""Tests for the app-factory CORS wiring (#146).

The API's CORS allow-list and the #104 CSRF Origin gate must derive from a
single normalized source (``Settings.cors_origins_list``). These tests prove the
``CORSMiddleware`` is configured from settings — not a separate ``os.getenv``
read — and that its allow-list is exactly the set ``enforce_csrf_origin`` checks
membership against, so the two controls can never silently drift.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import Settings
from src.main import create_app


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = dict(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="cors-test-secret",
    )
    base.update(overrides)
    return Settings(**base)


def _cors_kwargs(app: FastAPI) -> dict[str, Any]:
    """Read the declared CORSMiddleware config off the app's middleware stack."""
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware.kwargs
    raise AssertionError("CORSMiddleware is not configured on the app")


def test_cors_middleware_allow_origins_from_settings() -> None:
    # The middleware must receive the normalized single-source list, not a raw
    # comma split — mixed case and a trailing slash prove normalization ran.
    settings = _settings(cors_origins="HTTPS://A.EXAMPLE/, https://b.example")
    app = create_app(settings)
    allow_origins = _cors_kwargs(app)["allow_origins"]
    assert allow_origins == settings.cors_origins_list
    assert allow_origins == ["https://a.example", "https://b.example"]


def test_cors_allow_origins_equals_csrf_allow_list() -> None:
    # Single-source guarantee: the CORS allow-list is exactly the set the CSRF
    # gate checks against. enforce_csrf_origin now reads set(cors_origins_list),
    # so equality with cors_origins_list is equality with the CSRF allow-list.
    settings = _settings(cors_origins="https://a.example, https://b.example")
    app = create_app(settings)
    allow_origins = _cors_kwargs(app)["allow_origins"]
    assert set(allow_origins) == set(settings.cors_origins_list)


def test_cors_credentials_and_methods_unchanged() -> None:
    # Regression guard: the factory refactor preserved the non-origin CORS config
    # required for the httpOnly refresh cookie to round-trip.
    kwargs = _cors_kwargs(create_app(_settings()))
    assert kwargs["allow_credentials"] is True
    assert kwargs["allow_methods"] == ["GET", "POST"]
    assert kwargs["allow_headers"] == ["Content-Type", "Authorization"]


def test_create_app_uses_get_settings_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # Conftest-compatibility contract: create_app() with no argument must
    # resolve settings via src.main.get_settings *at call time*, so the existing
    # patch("src.main.get_settings", ...) in conftest keeps working.
    settings = _settings(cors_origins="https://patched.example")
    monkeypatch.setattr("src.main.get_settings", lambda: settings)
    app = create_app()
    assert _cors_kwargs(app)["allow_origins"] == ["https://patched.example"]
