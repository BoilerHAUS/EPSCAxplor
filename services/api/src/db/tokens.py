"""Refresh-token persistence backing rotation and reuse detection.

All functions take a caller-provided asyncpg connection so the service layer can
run mark-rotated + insert (and family revocation) inside one transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import asyncpg
from pydantic import BaseModel


class RefreshTokenRecord(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    token_hash: str
    family_id: uuid.UUID
    parent_id: uuid.UUID | None
    status: str
    expires_at: datetime
    created_at: datetime
    rotated_at: datetime | None


async def insert_refresh_token(
    conn: asyncpg.Connection,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    token_hash: str,
    family_id: uuid.UUID,
    expires_at: datetime,
    parent_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Insert a new active refresh token and return its id."""
    row = await conn.fetchrow(
        """
        INSERT INTO refresh_tokens
            (user_id, tenant_id, token_hash, family_id, parent_id, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        user_id,
        tenant_id,
        token_hash,
        family_id,
        parent_id,
        expires_at,
    )
    token_id: uuid.UUID = row["id"]
    return token_id


async def get_refresh_token_by_hash(
    conn: asyncpg.Connection, token_hash: str
) -> RefreshTokenRecord | None:
    """Look up a refresh token by its SHA-256 hash."""
    row = await conn.fetchrow(
        "SELECT * FROM refresh_tokens WHERE token_hash = $1",
        token_hash,
    )
    return RefreshTokenRecord.model_validate(dict(row)) if row is not None else None


async def mark_rotated(conn: asyncpg.Connection, token_id: uuid.UUID) -> int:
    """Transition an active token to 'rotated'; return the number of rows changed.

    The ``status = 'active'`` guard is the concurrency control: under READ
    COMMITTED, a racing rotation blocks on the row lock and then updates 0 rows,
    so a caller seeing 0 knows it lost the race and must treat the token as spent.
    """
    status = await conn.execute(
        "UPDATE refresh_tokens SET status = 'rotated', rotated_at = NOW() "
        "WHERE id = $1 AND status = 'active'",
        token_id,
    )
    # asyncpg returns a command tag like "UPDATE 1"; the trailing int is the count.
    return int(status.split()[-1])


async def revoke_family(conn: asyncpg.Connection, family_id: uuid.UUID) -> None:
    """Revoke every non-revoked token in a rotation family (reuse response)."""
    await conn.execute(
        "UPDATE refresh_tokens SET status = 'revoked' "
        "WHERE family_id = $1 AND status <> 'revoked'",
        family_id,
    )


async def revoke_all_for_user(conn: asyncpg.Connection, user_id: uuid.UUID) -> None:
    """Revoke every non-revoked token for a user (e.g. password reset)."""
    await conn.execute(
        "UPDATE refresh_tokens SET status = 'revoked' "
        "WHERE user_id = $1 AND status <> 'revoked'",
        user_id,
    )
