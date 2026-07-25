"""Database access helpers.

Request-path code shares one process-wide asyncpg pool (#147): the app lifespan
calls ``init_pool`` / ``close_pool`` and every route/service acquires through
``acquire()``. ``min_size=0`` is load-bearing — pool creation opens no
connection, so the app boots (and env-less test runs pass) even when Postgres
is unreachable; the first real connection happens on first acquire and /health
reports an outage instead of the process crash-looping.

``connect`` remains for callers with no app lifespan (operator scripts); the
``db/*`` helper modules are pool-agnostic — they take whatever connection the
caller provides.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from typing import cast

import asyncpg

DEFAULT_TIMEOUT = 5.0

POOL_MIN_SIZE = 0  # lazy: no connection is opened at create_pool time
POOL_MAX_SIZE = 10  # small VPS; Postgres is shared — treat 10 as this API's budget
# Three distinct timeout semantics, deliberately named apart:
POOL_CONNECT_TIMEOUT = 5.0  # TCP + auth handshake per new connection (asyncpg default: 60s)
POOL_COMMAND_TIMEOUT = 5.0  # per-statement cap on pooled connections (was unset pre-pool)
POOL_ACQUIRE_TIMEOUT = 5.0  # waiting for a free pool slot

_pool: asyncpg.Pool | None = None


async def init_pool(database_url: str) -> asyncpg.Pool:
    """Create (once) and return the process-wide connection pool.

    With ``min_size=0`` the pool also closes connections idle past asyncpg's
    default ``max_inactive_connection_lifetime`` (300s), so low traffic shows
    as connect/disconnect churn on the Postgres side — that is expected, not a
    leak. ``command_timeout`` bounds every statement on pooled connections,
    including the auth token-rotation transaction — a deliberate
    bounded-worst-case trade against the previously uncapped statements.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=POOL_MIN_SIZE,
            max_size=POOL_MAX_SIZE,
            # Forwarded to asyncpg.connect() for each physical connection;
            # without it a black-holed Postgres blocks acquires for 60s.
            timeout=POOL_CONNECT_TIMEOUT,
            command_timeout=POOL_COMMAND_TIMEOUT,
        )
    return _pool


async def close_pool() -> None:
    """Close the pool and reset the holder. Safe to call when uninitialized."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the pool, or raise if the lifespan has not initialized it."""
    if _pool is None:
        raise RuntimeError("database pool is not initialized; call init_pool() at startup")
    return _pool


@contextlib.asynccontextmanager
async def acquire() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a pooled connection, returning it to the pool on exit.

    The pooled proxy exposes the full ``asyncpg.Connection`` interface
    (including ``transaction()``), so callers are unchanged from ``connect``.
    """
    pool = get_pool()
    async with pool.acquire(timeout=POOL_ACQUIRE_TIMEOUT) as conn:
        yield cast(asyncpg.Connection, conn)


@contextlib.asynccontextmanager
async def connect(
    database_url: str, timeout: float = DEFAULT_TIMEOUT
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Open a single asyncpg connection and guarantee it is closed."""
    conn = await asyncpg.connect(database_url, timeout=timeout)
    try:
        yield conn
    finally:
        await conn.close()
