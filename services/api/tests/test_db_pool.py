"""Tests for the process-wide asyncpg connection pool (#147).

The pool is initialized once at app lifespan and shared by every request-path
DB access via ``db.acquire()``. ``min_size=0`` is load-bearing: pool creation
must not open any connection, so the app (and env-less test runs) boot even
when Postgres is unreachable.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.db as db


@pytest.fixture(autouse=True)
def _reset_pool() -> Generator[None, None, None]:
    """Isolate the module-level pool holder between tests."""
    db._pool = None
    yield
    db._pool = None


def _fake_pool() -> Any:
    pool = MagicMock()
    pool.close = AsyncMock()
    return pool


async def test_get_pool_raises_before_init() -> None:
    with pytest.raises(RuntimeError, match="not initialized"):
        db.get_pool()


async def test_init_pool_creates_lazily_and_stores() -> None:
    pool = _fake_pool()
    with patch("src.db.asyncpg.create_pool", new=AsyncMock(return_value=pool)) as created:
        result = await db.init_pool("postgresql://u:p@h/d")

    assert result is pool
    assert db.get_pool() is pool
    kwargs = created.call_args.kwargs
    # min_size=0 means create_pool opens no connection — boot resilience.
    assert kwargs["min_size"] == 0
    assert kwargs["max_size"] == db.POOL_MAX_SIZE
    # Connect timeout must be set explicitly: asyncpg's default is 60s, which
    # would let a black-holed Postgres hang request-path acquires.
    assert kwargs["timeout"] == db.POOL_CONNECT_TIMEOUT
    assert kwargs["command_timeout"] == db.POOL_COMMAND_TIMEOUT


async def test_init_pool_is_idempotent() -> None:
    pool = _fake_pool()
    with patch("src.db.asyncpg.create_pool", new=AsyncMock(return_value=pool)) as created:
        first = await db.init_pool("postgresql://u:p@h/d")
        second = await db.init_pool("postgresql://u:p@h/d")

    assert first is second
    assert created.await_count == 1


async def test_close_pool_closes_and_resets() -> None:
    pool = _fake_pool()
    with patch("src.db.asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        await db.init_pool("postgresql://u:p@h/d")

    await db.close_pool()

    pool.close.assert_awaited_once()
    with pytest.raises(RuntimeError):
        db.get_pool()


async def test_close_pool_is_noop_when_uninitialized() -> None:
    await db.close_pool()  # must not raise


async def test_acquire_yields_pooled_connection() -> None:
    conn = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    db._pool = pool

    async with db.acquire() as got:
        assert got is conn

    pool.acquire.assert_called_once()
    pool.acquire.return_value.__aexit__.assert_awaited_once()


async def test_acquire_raises_without_pool() -> None:
    with pytest.raises(RuntimeError, match="not initialized"):
        async with db.acquire():
            pass  # pragma: no cover
