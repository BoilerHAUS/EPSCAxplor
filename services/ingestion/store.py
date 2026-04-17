"""
Stage 6: Store — upsert embeddings to Qdrant and register documents in PostgreSQL.

For each ingested document:
1. Compute SHA-256 of the source PDF for change detection.
2. Upsert a row in the PostgreSQL `documents` table (idempotent — updates
   file_hash, chunk_count, and ingested_at on re-run).
3. Build Qdrant PointStructs with full metadata payload and upsert to the
   `epsca_chunks` collection.

Point IDs are deterministic: uuid5(NAMESPACE_URL, "{document_id}:{chunk_index}"),
so re-running the pipeline on the same document overwrites existing points rather
than creating duplicates.

Environment variables:
    QDRANT_URL:    Base URL for the Qdrant instance.  Default: http://127.0.0.1:6333
    POSTGRES_DSN:  asyncpg-compatible connection string.
                   Default: postgresql://epsca_user:password@localhost/epsca
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import uuid
from chunk import Chunk
from pathlib import Path

import asyncpg
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from classify import ClassifiedDocument

logger = logging.getLogger(__name__)

QDRANT_URL: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION: str = "epsca_chunks"
# No default — must be provided via environment or the postgres_dsn kwarg.
# Fail fast rather than silently connecting to the wrong host.
POSTGRES_DSN: str = os.getenv("POSTGRES_DSN", "")


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _compute_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _make_point_id(document_id: uuid.UUID, chunk_index: int) -> str:
    """Return a deterministic UUID string for a Qdrant point."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


async def _upsert_document_row(
    conn: asyncpg.Connection,
    doc: ClassifiedDocument,
    file_hash: str,
    chunk_count: int,
) -> uuid.UUID:
    """
    Insert or update the document row in PostgreSQL.

    Uses SELECT FOR UPDATE inside a serialised transaction to prevent duplicate
    inserts from concurrent pipeline runs on the same document.

    Returns the document's UUID.
    """
    source_filename = doc.extracted.source_path.name

    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT id FROM documents WHERE source_filename = $1 FOR UPDATE",
            source_filename,
        )

        if existing:
            row = await conn.fetchrow(
                """
                UPDATE documents
                   SET file_hash    = $1,
                       chunk_count  = $2,
                       ingested_at  = NOW(),
                       updated_at   = NOW()
                 WHERE id = $3
                 RETURNING id
                """,
                file_hash,
                chunk_count,
                existing["id"],
            )
        else:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (
                    union_name, document_type, agreement_scope,
                    title, source_url, source_filename,
                    effective_date, expiry_date,
                    file_hash, chunk_count, ingested_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                RETURNING id
                """,
                doc.metadata.union_name,
                doc.metadata.document_type,
                doc.metadata.agreement_scope,
                doc.metadata.title,
                doc.metadata.source_url,
                source_filename,
                datetime.date.fromisoformat(doc.metadata.effective_date),
                datetime.date.fromisoformat(doc.metadata.expiry_date) if doc.metadata.expiry_date else None,
                file_hash,
                chunk_count,
            )

    if row is None:
        raise RuntimeError(
            f"Expected RETURNING id after upsert for '{source_filename}', got nothing"
        )
    return row["id"]


def _build_points(
    document_id: uuid.UUID,
    doc: ClassifiedDocument,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> list[PointStruct]:
    """Build Qdrant PointStructs with full metadata payload."""
    source_filename = doc.extracted.source_path.name
    return [
        PointStruct(
            id=_make_point_id(document_id, chunk.chunk_index),
            vector=embeddings[i],
            payload={
                "document_id": str(document_id),
                "source_filename": source_filename,
                "union_name": doc.metadata.union_name,
                "document_type": doc.metadata.document_type,
                "agreement_scope": doc.metadata.agreement_scope,
                "effective_date": doc.metadata.effective_date,
                "expiry_date": doc.metadata.expiry_date,
                "chunk_index": chunk.chunk_index,
                "article_number": chunk.article_number,
                "article_title": chunk.article_title,
                "section_number": chunk.section_number,
                "page_number": chunk.page_number,
                "is_table": chunk.is_table,
                "text": chunk.text,
            },
        )
        for i, chunk in enumerate(chunks)
    ]


# ─── Public API ───────────────────────────────────────────────────────────────


async def store_document(
    doc: ClassifiedDocument,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    *,
    qdrant_url: str = QDRANT_URL,
    postgres_dsn: str = POSTGRES_DSN,
) -> None:
    """
    Persist a document's chunks and embeddings.

    Upserts a row into the PostgreSQL `documents` table, then upserts all
    chunk embeddings into the Qdrant `epsca_chunks` collection.  Safe to
    re-run — duplicate document rows are updated in place, and Qdrant points
    use deterministic IDs so they are overwritten rather than duplicated.

    Args:
        doc:          ClassifiedDocument produced by classify.py.
        chunks:       Chunks produced by chunk_document().
        embeddings:   Embedding vectors from embed_chunks(), same order as chunks.
        qdrant_url:   Qdrant base URL (overridable for testing).
        postgres_dsn: asyncpg-compatible DSN (overridable for testing).

    Raises:
        ValueError: If len(chunks) != len(embeddings).
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have "
            "the same length"
        )

    if not postgres_dsn:
        raise RuntimeError(
            "POSTGRES_DSN environment variable is required; "
            "set it to your asyncpg connection string."
        )

    file_hash = _compute_sha256(doc.extracted.source_path)

    async with asyncpg.create_pool(postgres_dsn) as pool:
        async with pool.acquire() as conn:
            document_id = await _upsert_document_row(conn, doc, file_hash, len(chunks))

    logger.info(
        "Registered document %s (id=%s, chunks=%d)",
        doc.extracted.source_path.name,
        document_id,
        len(chunks),
    )

    if not chunks:
        return

    points = _build_points(document_id, doc, chunks, embeddings)
    qdrant = AsyncQdrantClient(url=qdrant_url)
    try:
        await qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
        logger.info(
            "Upserted %d points to Qdrant collection '%s'",
            len(points),
            QDRANT_COLLECTION,
        )
    finally:
        await qdrant.close()
