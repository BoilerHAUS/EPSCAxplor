"""Tests for store.py — Stage 6 of the ingestion pipeline."""

from __future__ import annotations

import uuid
from chunk import Chunk
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from classify import ClassifiedDocument, DocumentMetadata
from extract import ExtractedDocument
from store import (
    QDRANT_COLLECTION,
    _make_point_id,
    store_document,
)

EMBED_DIM = 768
_TEST_DSN = "postgresql://test/test"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_metadata(
    union_name: str = "IBEW",
    document_type: str = "primary_ca",
    agreement_scope: str | None = "generation",
    effective_date: str = "2025-05-01",
    expiry_date: str | None = "2030-04-30",
    title: str = "IBEW Generation 2025-2030 Collective Agreement",
    source_url: str | None = "PLACEHOLDER",
) -> DocumentMetadata:
    return DocumentMetadata(
        union_name=union_name,
        document_type=document_type,
        agreement_scope=agreement_scope,
        effective_date=effective_date,
        expiry_date=expiry_date,
        title=title,
        source_url=source_url,
    )


def _make_doc(tmp_path: Path, filename: str = "ibew.pdf") -> ClassifiedDocument:
    pdf = tmp_path / filename
    pdf.write_bytes(b"%PDF-1.4 fake content for hashing")
    extracted = ExtractedDocument(source_path=pdf, blocks=[], page_count=1)
    return ClassifiedDocument(extracted=extracted, metadata=_make_metadata())


def _make_chunk(index: int = 0) -> Chunk:
    return Chunk(
        text=f"chunk text {index}",
        page_number=1,
        is_table=False,
        article_number="Article 1",
        section_number="1.01",
        article_title="Scope",
        chunk_index=index,
    )


def _fake_embedding() -> list[float]:
    return [0.1] * EMBED_DIM


def _make_pg_conn(
    document_id: uuid.UUID | None = None,
    *,
    existing: bool = True,
    row_after_upsert: dict | None = None,
) -> AsyncMock:
    """
    Build a mock asyncpg connection with a working transaction() context manager.

    When `existing=True` (default) the first fetchrow (SELECT FOR UPDATE) returns
    a row, triggering the UPDATE path.  When `existing=False` the SELECT returns
    None, triggering the INSERT path.

    `row_after_upsert` overrides the second fetchrow return value (UPDATE/INSERT
    RETURNING id).  Pass None explicitly to test the row=None error path.
    """
    doc_id = document_id or uuid.uuid4()
    returning_row = row_after_upsert if row_after_upsert is not None else {"id": doc_id}

    conn = AsyncMock()

    if existing:
        conn.fetchrow = AsyncMock(side_effect=[{"id": doc_id}, returning_row])
    else:
        conn.fetchrow = AsyncMock(side_effect=[None, returning_row])

    # asyncpg conn.transaction() is a sync call returning an async context manager
    tx_ctx = AsyncMock()
    tx_ctx.__aenter__ = AsyncMock(return_value=tx_ctx)
    tx_ctx.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=tx_ctx)

    return conn


def _make_pg_pool(conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool context manager."""
    pool = MagicMock()
    pool.__aenter__ = AsyncMock(return_value=pool)
    pool.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


def _make_qdrant_client() -> AsyncMock:
    client = AsyncMock()
    client.upsert = AsyncMock(return_value=None)
    client.close = AsyncMock(return_value=None)
    return client


# ─── Unit tests: _make_point_id ───────────────────────────────────────────────


class TestMakePointId:
    def test_returns_string(self) -> None:
        doc_id = uuid.uuid4()
        result = _make_point_id(doc_id, 0)
        assert isinstance(result, str)

    def test_valid_uuid_format(self) -> None:
        doc_id = uuid.uuid4()
        result = _make_point_id(doc_id, 0)
        parsed = uuid.UUID(result)
        assert str(parsed) == result

    def test_different_chunk_index_produces_different_id(self) -> None:
        doc_id = uuid.uuid4()
        id_0 = _make_point_id(doc_id, 0)
        id_1 = _make_point_id(doc_id, 1)
        assert id_0 != id_1

    def test_different_document_id_produces_different_id(self) -> None:
        doc_id_a = uuid.uuid4()
        doc_id_b = uuid.uuid4()
        id_a = _make_point_id(doc_id_a, 0)
        id_b = _make_point_id(doc_id_b, 0)
        assert id_a != id_b

    def test_deterministic_for_same_inputs(self) -> None:
        doc_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        id_1 = _make_point_id(doc_id, 5)
        id_2 = _make_point_id(doc_id, 5)
        assert id_1 == id_2


# ─── Integration tests: store_document ───────────────────────────────────────


class TestStoreDocumentPostgres:
    @pytest.mark.asyncio
    async def test_postgres_upsert_called(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=_make_qdrant_client()),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        # fetchrow is called at least once (SELECT FOR UPDATE + UPDATE or INSERT)
        assert conn.fetchrow.call_count >= 1

    @pytest.mark.asyncio
    async def test_postgres_wrapped_in_transaction(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=_make_qdrant_client()),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        conn.transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_receives_correct_union_name(self, tmp_path: Path) -> None:
        """INSERT path carries union_name — use existing=False to trigger it."""
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn(existing=False)
        pool = _make_pg_pool(conn)

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=_make_qdrant_client()),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        # All fetchrow args across SELECT + INSERT calls
        all_args = [arg for c in conn.fetchrow.call_args_list for arg in c.args]
        assert "IBEW" in all_args

    @pytest.mark.asyncio
    async def test_postgres_receives_chunk_count(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        n = 3
        chunks = [_make_chunk(i) for i in range(n)]
        embeddings = [_fake_embedding() for _ in range(n)]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=_make_qdrant_client()),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        all_args = [arg for c in conn.fetchrow.call_args_list for arg in c.args]
        assert n in all_args

    @pytest.mark.asyncio
    async def test_postgres_receives_source_filename(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path, "ibew.pdf")
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=_make_qdrant_client()),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        all_args = [arg for c in conn.fetchrow.call_args_list for arg in c.args]
        assert "ibew.pdf" in all_args

    @pytest.mark.asyncio
    async def test_row_none_after_upsert_raises_runtime_error(
        self, tmp_path: Path
    ) -> None:
        """If UPDATE/INSERT RETURNING yields no row, raise RuntimeError immediately."""
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        # existing=True, but the UPDATE RETURNING returns None (e.g. row deleted mid-tx)
        conn = _make_pg_conn(existing=True, row_after_upsert=None)
        # Override fetchrow: SELECT returns a row, UPDATE RETURNING yields None
        conn.fetchrow = AsyncMock(side_effect=[{"id": uuid.uuid4()}, None])
        tx_ctx = AsyncMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=tx_ctx)
        tx_ctx.__aexit__ = AsyncMock(return_value=False)
        conn.transaction = MagicMock(return_value=tx_ctx)
        pool = _make_pg_pool(conn)

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=_make_qdrant_client()),
        ):
            with pytest.raises(RuntimeError, match="Expected RETURNING id"):
                await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)


class TestStoreDocumentQdrant:
    @pytest.mark.asyncio
    async def test_qdrant_upsert_called_once(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)
        qdrant = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=qdrant),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_qdrant_upserts_to_correct_collection(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)
        qdrant = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=qdrant),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        call_kwargs = qdrant.upsert.call_args.kwargs
        assert call_kwargs["collection_name"] == QDRANT_COLLECTION

    @pytest.mark.asyncio
    async def test_qdrant_point_count_matches_chunks(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        n = 5
        chunks = [_make_chunk(i) for i in range(n)]
        embeddings = [_fake_embedding() for _ in range(n)]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)
        qdrant = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=qdrant),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        call_kwargs = qdrant.upsert.call_args.kwargs
        assert len(call_kwargs["points"]) == n

    @pytest.mark.asyncio
    async def test_qdrant_point_payload_has_union_name(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)
        qdrant = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=qdrant),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        points = qdrant.upsert.call_args.kwargs["points"]
        assert points[0].payload["union_name"] == "IBEW"

    @pytest.mark.asyncio
    async def test_qdrant_point_payload_has_text(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)
        qdrant = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=qdrant),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        points = qdrant.upsert.call_args.kwargs["points"]
        assert points[0].payload["text"] == "chunk text 0"

    @pytest.mark.asyncio
    async def test_qdrant_point_ids_are_deterministic(self, tmp_path: Path) -> None:
        """Re-running store_document produces the same point IDs (idempotent upsert)."""
        fixed_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]

        conn1 = _make_pg_conn(fixed_id)
        pool1 = _make_pg_pool(conn1)
        qdrant1 = _make_qdrant_client()

        conn2 = _make_pg_conn(fixed_id)
        pool2 = _make_pg_pool(conn2)
        qdrant2 = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool1),
            patch("store.AsyncQdrantClient", return_value=qdrant1),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        with (
            patch("store.asyncpg.create_pool", return_value=pool2),
            patch("store.AsyncQdrantClient", return_value=qdrant2),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        id_run1 = qdrant1.upsert.call_args.kwargs["points"][0].id
        id_run2 = qdrant2.upsert.call_args.kwargs["points"][0].id
        assert id_run1 == id_run2

    @pytest.mark.asyncio
    async def test_qdrant_close_called_after_upsert(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)
        qdrant = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=qdrant),
        ):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

        qdrant.close.assert_called_once()


class TestStoreDocumentValidation:
    @pytest.mark.asyncio
    async def test_mismatched_chunks_and_embeddings_raises(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0), _make_chunk(1)]
        embeddings = [_fake_embedding()]  # too few

        with pytest.raises(ValueError, match="chunks"):
            await store_document(doc, chunks, embeddings, postgres_dsn=_TEST_DSN)

    @pytest.mark.asyncio
    async def test_missing_postgres_dsn_raises_runtime_error(
        self, tmp_path: Path
    ) -> None:
        doc = _make_doc(tmp_path)
        chunks = [_make_chunk(0)]
        embeddings = [_fake_embedding()]

        with pytest.raises(RuntimeError, match="POSTGRES_DSN"):
            await store_document(doc, chunks, embeddings, postgres_dsn="")

    @pytest.mark.asyncio
    async def test_empty_chunks_skips_qdrant(self, tmp_path: Path) -> None:
        doc = _make_doc(tmp_path)
        conn = _make_pg_conn()
        pool = _make_pg_pool(conn)
        qdrant = _make_qdrant_client()

        with (
            patch("store.asyncpg.create_pool", return_value=pool),
            patch("store.AsyncQdrantClient", return_value=qdrant),
        ):
            await store_document(doc, [], [], postgres_dsn=_TEST_DSN)

        qdrant.upsert.assert_not_called()
