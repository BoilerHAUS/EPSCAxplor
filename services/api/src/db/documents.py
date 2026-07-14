"""documents registry reads for GET /documents (#26)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import asyncpg
from pydantic import BaseModel


class DocumentRecord(BaseModel):
    id: uuid.UUID
    union_name: str
    document_type: str
    title: str
    effective_date: date | None
    expiry_date: date | None
    is_expired: bool
    chunk_count: int | None
    ingested_at: datetime | None


async def list_documents(
    conn: asyncpg.Connection,
    *,
    union_name: str | None = None,
    document_type: str | None = None,
    is_expired: bool | None = None,
) -> list[DocumentRecord]:
    """List corpus documents, optionally filtered.

    Uses a single static, fully-parameterized query (``$N IS NULL OR col = $N``)
    so there is no dynamically-assembled SQL regardless of which filters are set.
    """
    rows = await conn.fetch(
        """
        SELECT id, union_name, document_type, title, effective_date, expiry_date,
               is_expired, chunk_count, ingested_at
        FROM documents
        WHERE ($1::text IS NULL OR union_name = $1)
          AND ($2::text IS NULL OR document_type = $2)
          AND ($3::boolean IS NULL OR is_expired = $3)
        ORDER BY union_name, title
        """,
        union_name,
        document_type,
        is_expired,
    )
    return [DocumentRecord.model_validate(dict(row)) for row in rows]
