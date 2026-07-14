"""Database access helpers.

Provides a single ``connect`` context manager so callers that need a
transaction (e.g. refresh-token rotation) can share one connection across
several statements. Read-only routes elsewhere still open their own short-lived
connections directly; this helper is additive, not a migration of that code.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator

import asyncpg

DEFAULT_TIMEOUT = 5.0


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
