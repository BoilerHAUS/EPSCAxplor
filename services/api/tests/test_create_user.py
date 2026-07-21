"""Tests for scripts/create_user.py — the operator user-seeding CLI (#23)."""

from __future__ import annotations

import contextlib
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from scripts.create_user import _create_user, _parse_args, _resolve_database_url
from src.db.subscriptions import SubscriptionRecord


def test_parse_args_applies_role_default() -> None:
    args = _parse_args(["--tenant-slug", "system", "--email", "a@b.c"])
    assert args.tenant_slug == "system"
    assert args.email == "a@b.c"
    assert args.role == "member"


def test_parse_args_rejects_invalid_role() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--tenant-slug", "system", "--email", "a@b.c", "--role", "superuser"])


def test_resolve_database_url_prefers_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    assert _resolve_database_url("postgresql://explicit") == "postgresql://explicit"


def test_resolve_database_url_errors_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    with pytest.raises(SystemExit):
        _resolve_database_url(None)


async def test_create_user_hashes_password_and_returns_id() -> None:
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=uuid.uuid4())  # existing tenant id
    conn.fetchrow = AsyncMock(return_value={"id": new_id})

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_user.connect", _fake_connect), patch(
        "scripts.create_user.get_tenant_subscription", new=AsyncMock(return_value=None)
    ):
        result = await _create_user(
            tenant_slug="system",
            email="a@b.c",
            role="owner",
            password="s3kr3t",
            rounds=4,
            database_url="postgresql://x",
        )

    assert result == new_id
    # The stored value is a bcrypt hash, never the plaintext.
    stored_hash = conn.fetchrow.await_args.args[3]
    assert stored_hash.startswith("$2b$")
    assert stored_hash != "s3kr3t"


async def test_create_user_stores_normalized_email() -> None:
    """Emails are stored lowercased so the LOWER(email) unique index holds (#141)."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=uuid.uuid4())  # existing tenant id
    conn.fetchrow = AsyncMock(return_value={"id": uuid.uuid4()})

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_user.connect", _fake_connect), patch(
        "scripts.create_user.get_tenant_subscription", new=AsyncMock(return_value=None)
    ):
        await _create_user(
            tenant_slug="system",
            email="  You@Example.COM ",
            role="member",
            password="pw",
            rounds=4,
            database_url="postgresql://x",
        )

    stored_email = conn.fetchrow.await_args.args[2]
    assert stored_email == "you@example.com"


async def test_create_user_errors_when_tenant_missing() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)  # no such tenant

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_user.connect", _fake_connect):
        with pytest.raises(SystemExit):
            await _create_user(
                tenant_slug="ghost",
                email="a@b.c",
                role="member",
                password="pw",
                rounds=4,
                database_url="postgresql://x",
            )


async def test_create_user_rejected_when_at_user_limit() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=uuid.uuid4())  # existing tenant id
    sub = SubscriptionRecord(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tier="individual",
        status="active",
        query_limit_monthly=100,
        user_limit=1,
        current_period_start=None,
        current_period_end=None,
    )

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_user.connect", _fake_connect), patch(
        "scripts.create_user.get_tenant_subscription", new=AsyncMock(return_value=sub)
    ), patch(
        "scripts.create_user.count_users_for_tenant", new=AsyncMock(return_value=1)
    ):
        with pytest.raises(SystemExit):
            await _create_user(
                tenant_slug="acme",
                email="new@b.c",
                role="member",
                password="pw",
                rounds=4,
                database_url="postgresql://x",
            )
    # user was at the limit, so no INSERT happened
    conn.fetchrow.assert_not_awaited()


async def test_create_user_rejects_empty_after_normalize_email() -> None:
    """A whitespace-only --email collapses to '' and must be refused, not stored (#141)."""
    conn = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_user.connect", _fake_connect):
        with pytest.raises(SystemExit):
            await _create_user(
                tenant_slug="system",
                email="   ",
                role="member",
                password="pw",
                rounds=4,
                database_url="postgresql://x",
            )
    conn.fetchrow.assert_not_awaited()


async def test_create_user_rejects_non_ascii_email() -> None:
    """Non-ASCII email is refused at the ingress so app + DB case-folding can't desync (#141)."""
    conn = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_connect(*_a: object, **_k: object) -> Any:
        yield conn

    with patch("scripts.create_user.connect", _fake_connect):
        with pytest.raises(SystemExit):
            await _create_user(
                tenant_slug="system",
                email="İstanbul@x.com",
                role="member",
                password="pw",
                rounds=4,
                database_url="postgresql://x",
            )
    conn.fetchrow.assert_not_awaited()
