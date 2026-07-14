"""Tests for src/auth/service.py — login, rotation, reuse detection (#23)."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.auth.passwords import hash_password
from src.auth.service import (
    AuthError,
    TokenPair,
    login,
    revoke_refresh_token,
    rotate_refresh_token,
)
from src.auth.tokens import decode_access_token
from src.config import Settings
from src.db.tokens import RefreshTokenRecord
from src.db.users import UserRecord

JWT_SECRET = "service-test-secret"  # noqa: S105


# ─── Fakes: async connection + transaction that do nothing ────────────────────


class _FakeTxn:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeConn:
    def transaction(self) -> _FakeTxn:
        return _FakeTxn()


@contextlib.asynccontextmanager
async def _fake_connect(*_a: object, **_k: object) -> Any:
    yield _FakeConn()


def _settings() -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret=JWT_SECRET,
    )


def _user(
    *,
    is_active: bool = True,
    password: str = "secret",  # noqa: S107
    role: str = "owner",
    uid: uuid.UUID | None = None,
    tenant: uuid.UUID | None = None,
) -> UserRecord:
    return UserRecord(
        id=uid or uuid.uuid4(),
        tenant_id=tenant or uuid.uuid4(),
        email="a@b.c",
        password_hash=hash_password(password, rounds=4),
        role=role,
        is_active=is_active,
    )


def _token_record(
    *,
    status: str = "active",
    days: int = 7,
    uid: uuid.UUID | None = None,
    tenant: uuid.UUID | None = None,
) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        id=uuid.uuid4(),
        user_id=uid or uuid.uuid4(),
        tenant_id=tenant or uuid.uuid4(),
        token_hash="h",
        family_id=uuid.uuid4(),
        parent_id=None,
        status=status,
        expires_at=datetime.now(UTC) + timedelta(days=days),
        created_at=datetime.now(UTC),
        rotated_at=None,
    )


@contextlib.contextmanager
def _service_env(**overrides: AsyncMock) -> Iterator[dict[str, AsyncMock]]:
    """Patch connect + every db call the service makes. Overrides set returns."""
    mocks: dict[str, AsyncMock] = {
        "get_user_by_email": AsyncMock(return_value=None),
        "get_user_by_id": AsyncMock(return_value=None),
        "get_refresh_token_by_hash": AsyncMock(return_value=None),
        "insert_refresh_token": AsyncMock(return_value=uuid.uuid4()),
        "mark_rotated": AsyncMock(return_value=1),
        "revoke_family": AsyncMock(),
        "touch_last_login": AsyncMock(),
    }
    mocks.update(overrides)
    with ExitStack() as stack:
        stack.enter_context(patch("src.auth.service.connect", _fake_connect))
        for name, mock in mocks.items():
            stack.enter_context(patch(f"src.auth.service.{name}", new=mock))
        yield mocks


# ─── login ────────────────────────────────────────────────────────────────────


async def test_login_success_issues_valid_pair() -> None:
    settings = _settings()
    user = _user(password="secret", role="admin")
    with _service_env(get_user_by_email=AsyncMock(return_value=user)) as m:
        pair = await login(settings, "a@b.c", "secret")

    assert isinstance(pair, TokenPair)
    assert pair.refresh_token
    assert pair.expires_in == settings.jwt_access_expiry_seconds
    claims = decode_access_token(pair.access_token, JWT_SECRET)
    assert claims.sub == user.id
    assert claims.tenant_id == user.tenant_id
    assert claims.role == "admin"
    m["insert_refresh_token"].assert_awaited_once()
    m["touch_last_login"].assert_awaited_once()


async def test_login_wrong_password_raises() -> None:
    with _service_env(get_user_by_email=AsyncMock(return_value=_user(password="right"))):
        with pytest.raises(AuthError):
            await login(_settings(), "a@b.c", "wrong")


async def test_login_unknown_email_raises() -> None:
    with _service_env(get_user_by_email=AsyncMock(return_value=None)):
        with pytest.raises(AuthError):
            await login(_settings(), "missing@b.c", "whatever")


async def test_login_inactive_user_raises_even_with_right_password() -> None:
    inactive = _user(password="secret", is_active=False)
    with _service_env(get_user_by_email=AsyncMock(return_value=inactive)):
        with pytest.raises(AuthError):
            await login(_settings(), "a@b.c", "secret")


async def test_login_error_message_identical_for_unknown_and_wrong() -> None:
    settings = _settings()
    with _service_env(get_user_by_email=AsyncMock(return_value=None)):
        with pytest.raises(AuthError) as unknown:
            await login(settings, "missing@b.c", "whatever")
    with _service_env(get_user_by_email=AsyncMock(return_value=_user(password="right"))):
        with pytest.raises(AuthError) as wrong:
            await login(settings, "a@b.c", "wrong")
    assert str(unknown.value) == str(wrong.value)


# ─── rotation ─────────────────────────────────────────────────────────────────


async def test_rotate_happy_path_marks_old_and_inserts_new() -> None:
    settings = _settings()
    rec = _token_record(status="active")
    user = _user(uid=rec.user_id, tenant=rec.tenant_id, role="member")
    with _service_env(
        get_refresh_token_by_hash=AsyncMock(return_value=rec),
        get_user_by_id=AsyncMock(return_value=user),
        mark_rotated=AsyncMock(return_value=1),
    ) as m:
        pair = await rotate_refresh_token(settings, "raw-token")

    m["mark_rotated"].assert_awaited_once()
    m["insert_refresh_token"].assert_awaited_once()
    m["revoke_family"].assert_not_awaited()
    assert pair.refresh_token != "raw-token"
    claims = decode_access_token(pair.access_token, JWT_SECRET)
    assert claims.sub == rec.user_id
    assert claims.role == "member"


async def test_rotate_replay_of_spent_token_revokes_family_and_raises() -> None:
    rec = _token_record(status="rotated")
    with _service_env(
        get_refresh_token_by_hash=AsyncMock(return_value=rec),
    ) as m:
        with pytest.raises(AuthError):
            await rotate_refresh_token(_settings(), "raw-token")

    m["revoke_family"].assert_awaited_once()
    m["mark_rotated"].assert_not_awaited()
    m["insert_refresh_token"].assert_not_awaited()


async def test_rotate_missing_token_raises() -> None:
    with _service_env(get_refresh_token_by_hash=AsyncMock(return_value=None)) as m:
        with pytest.raises(AuthError):
            await rotate_refresh_token(_settings(), "raw-token")
    m["revoke_family"].assert_not_awaited()


async def test_rotate_revoked_token_raises_without_new_writes() -> None:
    rec = _token_record(status="revoked")
    with _service_env(get_refresh_token_by_hash=AsyncMock(return_value=rec)) as m:
        with pytest.raises(AuthError):
            await rotate_refresh_token(_settings(), "raw-token")
    m["mark_rotated"].assert_not_awaited()
    m["insert_refresh_token"].assert_not_awaited()


async def test_rotate_expired_active_token_raises() -> None:
    rec = _token_record(status="active", days=-1)
    with _service_env(get_refresh_token_by_hash=AsyncMock(return_value=rec)) as m:
        with pytest.raises(AuthError):
            await rotate_refresh_token(_settings(), "raw-token")
    m["mark_rotated"].assert_not_awaited()


async def test_rotate_inactive_user_revokes_family_and_raises() -> None:
    rec = _token_record(status="active")
    inactive = _user(uid=rec.user_id, is_active=False)
    with _service_env(
        get_refresh_token_by_hash=AsyncMock(return_value=rec),
        get_user_by_id=AsyncMock(return_value=inactive),
    ) as m:
        with pytest.raises(AuthError):
            await rotate_refresh_token(_settings(), "raw-token")
    m["revoke_family"].assert_awaited_once()
    m["insert_refresh_token"].assert_not_awaited()


async def test_rotate_lost_race_revokes_family_and_raises() -> None:
    rec = _token_record(status="active")
    user = _user(uid=rec.user_id, tenant=rec.tenant_id)
    with _service_env(
        get_refresh_token_by_hash=AsyncMock(return_value=rec),
        get_user_by_id=AsyncMock(return_value=user),
        mark_rotated=AsyncMock(return_value=0),  # someone else rotated first
    ) as m:
        with pytest.raises(AuthError):
            await rotate_refresh_token(_settings(), "raw-token")
    m["revoke_family"].assert_awaited_once()
    m["insert_refresh_token"].assert_not_awaited()


# ─── revoke (logout) ──────────────────────────────────────────────────────────


async def test_revoke_unknown_token_is_noop() -> None:
    with _service_env(get_refresh_token_by_hash=AsyncMock(return_value=None)) as m:
        await revoke_refresh_token(_settings(), "raw-token")
    m["revoke_family"].assert_not_awaited()


async def test_revoke_known_token_revokes_family() -> None:
    rec = _token_record()
    with _service_env(get_refresh_token_by_hash=AsyncMock(return_value=rec)) as m:
        await revoke_refresh_token(_settings(), "raw-token")
    m["revoke_family"].assert_awaited_once()
