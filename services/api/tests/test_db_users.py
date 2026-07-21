"""Tests for src/db/users.py and the src.db.connect helper (#23)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

from src.db import connect
from src.db.users import UserRecord, get_user_by_email, touch_last_login

USER_ROW = {
    "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
    "tenant_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
    "email": "a@b.c",
    "password_hash": "$2b$12$notarealhash",  # noqa: S106
    "role": "owner",
    "is_active": True,
}


async def test_get_user_by_email_returns_record() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=USER_ROW)
    rec = await get_user_by_email(conn, "a@b.c")
    assert isinstance(rec, UserRecord)
    assert rec.email == "a@b.c"
    assert rec.role == "owner"
    assert rec.is_active is True
    conn.fetchrow.assert_awaited_once()


async def test_get_user_by_email_returns_none_when_absent() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    assert await get_user_by_email(conn, "missing@b.c") is None


async def test_get_user_by_email_normalizes_and_matches_case_insensitively() -> None:
    """Login is case-insensitive (#141): the lookup lowercases its argument and
    compares against ``LOWER(email)`` so mixed-case input still finds the row."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=USER_ROW)
    await get_user_by_email(conn, "  You@B.C ")
    sql, bound = conn.fetchrow.await_args.args[0], conn.fetchrow.await_args.args[1]
    assert "LOWER(email) = $1" in sql
    assert bound == "you@b.c"


async def test_touch_last_login_executes_update_with_user_id() -> None:
    conn = AsyncMock()
    uid = uuid.uuid4()
    await touch_last_login(conn, uid)
    conn.execute.assert_awaited_once()
    assert conn.execute.await_args.args[1] == uid


async def test_connect_opens_and_always_closes() -> None:
    fake_conn = AsyncMock()
    with patch("src.db.asyncpg.connect", new=AsyncMock(return_value=fake_conn)) as opened:
        async with connect("postgresql://x") as c:
            assert c is fake_conn
    opened.assert_awaited_once()
    fake_conn.close.assert_awaited_once()
