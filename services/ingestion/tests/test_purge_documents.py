"""Tests for purge_documents.py — orphaned-document cleanup (issue #178).

When a wage schedule is reissued its manifest source_filename changes, so a
reingest inserts a fresh row/points and orphans the old document's Postgres row
and Qdrant chunks.  purge_documents removes those by their old source_filename.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from purge_documents import PurgeResult, purge_documents

_TEST_DSN = "postgresql://test/test"
_TEST_API_KEY = "ingest-secret-key"  # noqa: S105
_OLD_NAME = "E-10-C LU 353 Oshawa-Port Hope - May 1, 2025.pdf"


def _make_conn(rows: list[dict]) -> AsyncMock:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=rows)
    conn.execute = AsyncMock(return_value="DELETE 1")
    return conn


def _make_pool(conn: AsyncMock) -> MagicMock:
    pool = MagicMock()
    pool.__aenter__ = AsyncMock(return_value=pool)
    pool.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


def _make_qdrant() -> AsyncMock:
    q = AsyncMock()
    q.delete = AsyncMock(return_value=None)
    q.close = AsyncMock(return_value=None)
    return q


class TestPurgeDocuments:
    @pytest.mark.asyncio
    async def test_deletes_qdrant_points_then_pg_row(self) -> None:
        doc_id = uuid.uuid4()
        conn = _make_conn([{"id": doc_id, "source_filename": _OLD_NAME}])
        qdrant = _make_qdrant()

        with (
            patch("purge_documents.asyncpg.create_pool", return_value=_make_pool(conn)),
            patch("purge_documents.AsyncQdrantClient", return_value=qdrant),
        ):
            result = await purge_documents([_OLD_NAME], postgres_dsn=_TEST_DSN)

        # Qdrant points deleted by document_id, then the Postgres row deleted.
        qdrant.delete.assert_called_once()
        selector_filter = qdrant.delete.call_args.kwargs["points_selector"].filter
        condition = selector_filter.must[0]
        assert condition.key == "document_id"
        assert condition.match.value == str(doc_id)
        conn.execute.assert_awaited_once()
        assert doc_id in conn.execute.call_args.args
        assert result.purged == [(_OLD_NAME, str(doc_id))]
        assert result.not_found == []
        qdrant.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dry_run_deletes_nothing(self) -> None:
        doc_id = uuid.uuid4()
        conn = _make_conn([{"id": doc_id, "source_filename": _OLD_NAME}])
        qdrant = _make_qdrant()

        with (
            patch("purge_documents.asyncpg.create_pool", return_value=_make_pool(conn)),
            patch("purge_documents.AsyncQdrantClient", return_value=qdrant),
        ):
            result = await purge_documents([_OLD_NAME], dry_run=True, postgres_dsn=_TEST_DSN)

        qdrant.delete.assert_not_called()
        conn.execute.assert_not_called()
        # The preview still reports what WOULD be purged.
        assert result.purged == [(_OLD_NAME, str(doc_id))]

    @pytest.mark.asyncio
    async def test_unknown_filename_reported_not_found(self) -> None:
        conn = _make_conn([])  # nothing matches in `documents`
        qdrant = _make_qdrant()

        with (
            patch("purge_documents.asyncpg.create_pool", return_value=_make_pool(conn)),
            patch("purge_documents.AsyncQdrantClient", return_value=qdrant) as mock_cls,
        ):
            result = await purge_documents(["ghost.pdf"], postgres_dsn=_TEST_DSN)

        assert result.purged == []
        assert result.not_found == ["ghost.pdf"]
        # No Qdrant client is even constructed when there is nothing to delete.
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_match_purges_found_and_reports_missing(self) -> None:
        doc_id = uuid.uuid4()
        conn = _make_conn([{"id": doc_id, "source_filename": _OLD_NAME}])
        qdrant = _make_qdrant()

        with (
            patch("purge_documents.asyncpg.create_pool", return_value=_make_pool(conn)),
            patch("purge_documents.AsyncQdrantClient", return_value=qdrant),
        ):
            result = await purge_documents(
                [_OLD_NAME, "ghost.pdf"], postgres_dsn=_TEST_DSN
            )

        assert [name for name, _ in result.purged] == [_OLD_NAME]
        assert result.not_found == ["ghost.pdf"]

    @pytest.mark.asyncio
    async def test_empty_input_touches_no_db(self) -> None:
        with patch("purge_documents.asyncpg.create_pool") as mock_pool:
            result = await purge_documents([], postgres_dsn=_TEST_DSN)
        assert result == PurgeResult()
        mock_pool.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_dsn_raises(self) -> None:
        with pytest.raises(RuntimeError, match="POSTGRES_DSN"):
            await purge_documents([_OLD_NAME], postgres_dsn="")

    @pytest.mark.asyncio
    async def test_forwards_qdrant_api_key(self) -> None:
        doc_id = uuid.uuid4()
        conn = _make_conn([{"id": doc_id, "source_filename": _OLD_NAME}])

        with (
            patch("purge_documents.asyncpg.create_pool", return_value=_make_pool(conn)),
            patch(
                "purge_documents.AsyncQdrantClient", return_value=_make_qdrant()
            ) as mock_cls,
        ):
            await purge_documents(
                [_OLD_NAME],
                qdrant_url="http://qd:6333",
                qdrant_api_key=_TEST_API_KEY,
                postgres_dsn=_TEST_DSN,
            )

        mock_cls.assert_called_once_with(url="http://qd:6333", api_key=_TEST_API_KEY)
