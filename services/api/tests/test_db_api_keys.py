"""Tests for src/db/api_keys.py (#24)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

from src.db.api_keys import (
    ApiKeyRecord,
    get_active_api_key_by_hash,
    insert_api_key,
    touch_last_used,
)


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Production key",
        "is_active": True,
    }
    base.update(overrides)
    return base


async def test_get_active_returns_record() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=_row())
    rec = await get_active_api_key_by_hash(conn, "somehash")
    assert isinstance(rec, ApiKeyRecord)
    assert rec.name == "Production key"
    assert rec.is_active is True


async def test_get_active_returns_none_when_absent_or_inactive() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)  # SQL filters is_active
    assert await get_active_api_key_by_hash(conn, "nope") is None


async def test_insert_returns_new_id() -> None:
    new_id = uuid.uuid4()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": new_id})
    got = await insert_api_key(
        conn, tenant_id=uuid.uuid4(), key_hash="somehash", name="Prod"
    )
    assert got == new_id
    conn.fetchrow.assert_awaited_once()


async def test_touch_last_used_targets_id() -> None:
    conn = AsyncMock()
    kid = uuid.uuid4()
    await touch_last_used(conn, kid)
    conn.execute.assert_awaited_once()
    assert conn.execute.await_args.args[1] == kid
