"""Tests for src/db/tokens.py (#23)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

from src.db.tokens import (
    RefreshTokenRecord,
    get_refresh_token_by_hash,
    insert_refresh_token,
    mark_rotated,
    revoke_all_for_user,
    revoke_family,
)


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "token_hash": "h",
        "family_id": uuid.uuid4(),
        "parent_id": None,
        "status": "active",
        "expires_at": datetime.now(UTC) + timedelta(days=7),
        "created_at": datetime.now(UTC),
        "rotated_at": None,
    }
    base.update(overrides)
    return base


async def test_insert_returns_new_id() -> None:
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": new_id})
    got = await insert_refresh_token(
        conn,
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        token_hash="h",  # noqa: S106 — opaque test value, not a secret
        family_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    assert got == new_id
    conn.fetchrow.assert_awaited_once()


async def test_get_by_hash_returns_record() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=_row(status="rotated"))
    rec = await get_refresh_token_by_hash(conn, "h")
    assert isinstance(rec, RefreshTokenRecord)
    assert rec.status == "rotated"


async def test_get_by_hash_returns_none_when_absent() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    assert await get_refresh_token_by_hash(conn, "nope") is None


async def test_mark_rotated_targets_token_id_and_returns_rowcount() -> None:
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    tid = uuid.uuid4()
    changed = await mark_rotated(conn, tid)
    assert changed == 1
    conn.execute.assert_awaited_once()
    assert conn.execute.await_args.args[1] == tid


async def test_mark_rotated_returns_zero_when_not_active() -> None:
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 0")
    assert await mark_rotated(conn, uuid.uuid4()) == 0


async def test_revoke_family_targets_family_id() -> None:
    conn = AsyncMock()
    fid = uuid.uuid4()
    await revoke_family(conn, fid)
    conn.execute.assert_awaited_once()
    assert conn.execute.await_args.args[1] == fid


async def test_revoke_all_for_user_targets_user_id() -> None:
    conn = AsyncMock()
    uid = uuid.uuid4()
    await revoke_all_for_user(conn, uid)
    conn.execute.assert_awaited_once()
    assert conn.execute.await_args.args[1] == uid
