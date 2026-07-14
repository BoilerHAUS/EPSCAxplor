"""User lookups against the ``users`` table.

Functions take a caller-provided asyncpg connection (see ``src.db.connect``) so
they compose with transactions when needed.
"""

from __future__ import annotations

import uuid

import asyncpg
from pydantic import BaseModel


class UserRecord(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    password_hash: str
    role: str
    is_active: bool


async def get_user_by_email(conn: asyncpg.Connection, email: str) -> UserRecord | None:
    """Return the user with this email, or None if there is no match."""
    row = await conn.fetchrow(
        "SELECT id, tenant_id, email, password_hash, role, is_active "
        "FROM users WHERE email = $1",
        email,
    )
    return UserRecord.model_validate(dict(row)) if row is not None else None


async def get_user_by_id(conn: asyncpg.Connection, user_id: uuid.UUID) -> UserRecord | None:
    """Return the user with this id, or None. Used on refresh to re-check that a
    user is still active before minting a new access token."""
    row = await conn.fetchrow(
        "SELECT id, tenant_id, email, password_hash, role, is_active "
        "FROM users WHERE id = $1",
        user_id,
    )
    return UserRecord.model_validate(dict(row)) if row is not None else None


async def touch_last_login(conn: asyncpg.Connection, user_id: uuid.UUID) -> None:
    """Stamp ``last_login_at = NOW()`` for a successful login."""
    await conn.execute("UPDATE users SET last_login_at = NOW() WHERE id = $1", user_id)
