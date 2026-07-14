"""Tests for scripts/create_api_key.py (#24)."""

from __future__ import annotations

import contextlib
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from scripts.create_api_key import _create_api_key, _parse_args, _resolve_database_url
from src.auth.api_keys import API_KEY_PREFIX


def test_parse_args_reads_slug_and_name() -> None:
    args = _parse_args(["--tenant-slug", "acme", "--name", "Prod"])
    assert args.tenant_slug == "acme"
    assert args.name == "Prod"


def test_parse_args_requires_name() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--tenant-slug", "acme"])


def test_resolve_database_url_errors_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    with pytest.raises(SystemExit):
        _resolve_database_url(None)


async def test_create_returns_prefixed_key_and_stores_only_hash() -> None:
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=uuid.uuid4())  # existing tenant id
    conn.fetchrow = AsyncMock(return_value={"id": new_id})

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_api_key.connect", _fake_connect):
        key_id, raw_key = await _create_api_key(
            tenant_slug="acme", name="Prod", database_url="postgresql://x"
        )

    assert key_id == new_id
    assert raw_key.startswith(API_KEY_PREFIX)
    # INSERT args: [0]=SQL, [1]=tenant_id, [2]=key_hash, [3]=name
    stored_hash = conn.fetchrow.await_args.args[2]
    assert stored_hash != raw_key
    assert len(stored_hash) == 64


async def test_create_errors_when_tenant_missing() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_api_key.connect", _fake_connect):
        with pytest.raises(SystemExit):
            await _create_api_key(
                tenant_slug="ghost", name="x", database_url="postgresql://x"
            )
