"""api_keys persistence for enterprise API-key auth (#24).

Takes a caller-provided asyncpg connection (see ``src.db.connect``), like the
rest of the db layer.
"""

from __future__ import annotations

import uuid

import asyncpg
from pydantic import BaseModel


class ApiKeyRecord(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    is_active: bool


async def get_active_api_key_by_hash(
    conn: asyncpg.Connection, key_hash: str
) -> ApiKeyRecord | None:
    """Return the active key for this hash, or None (unknown or deactivated).

    Filtering ``is_active`` in SQL means an unknown key and a revoked key are
    indistinguishable to the caller — both become a uniform 401.
    """
    row = await conn.fetchrow(
        "SELECT id, tenant_id, name, is_active FROM api_keys "
        "WHERE key_hash = $1 AND is_active = TRUE",
        key_hash,
    )
    return ApiKeyRecord.model_validate(dict(row)) if row is not None else None


async def insert_api_key(
    conn: asyncpg.Connection,
    *,
    tenant_id: uuid.UUID,
    key_hash: str,
    name: str,
) -> uuid.UUID:
    """Insert a new active API key (storing only its hash); return its id."""
    row = await conn.fetchrow(
        "INSERT INTO api_keys (tenant_id, key_hash, name) VALUES ($1, $2, $3) RETURNING id",
        tenant_id,
        key_hash,
        name,
    )
    new_id: uuid.UUID = row["id"]
    return new_id


async def touch_last_used(conn: asyncpg.Connection, api_key_id: uuid.UUID) -> None:
    """Stamp ``last_used_at = NOW()`` after a successful authentication."""
    await conn.execute("UPDATE api_keys SET last_used_at = NOW() WHERE id = $1", api_key_id)
