"""Tests for src/db/documents.py (#26)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any
from unittest.mock import AsyncMock

from src.db.documents import DocumentRecord, list_documents


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "union_name": "IBEW",
        "document_type": "primary_ca",
        "title": "IBEW Generation 2025-2030 Collective Agreement",
        "effective_date": date(2025, 5, 1),
        "expiry_date": date(2030, 4, 30),
        "is_expired": False,
        "chunk_count": 312,
        "ingested_at": datetime(2026, 4, 15),
    }
    base.update(overrides)
    return base


async def test_list_returns_records() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[_row(), _row(union_name="Sheet Metal Workers")])
    docs = await list_documents(conn)
    assert len(docs) == 2
    assert all(isinstance(d, DocumentRecord) for d in docs)
    assert docs[0].union_name == "IBEW"


async def test_list_passes_filters_as_bound_params() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    await list_documents(conn, union_name="IBEW", document_type="primary_ca", is_expired=False)
    args = conn.fetch.await_args.args
    # args[0]=SQL, then the three filter params in order
    assert args[1] == "IBEW"
    assert args[2] == "primary_ca"
    assert args[3] is False


async def test_list_empty_returns_empty_list() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    assert await list_documents(conn) == []
