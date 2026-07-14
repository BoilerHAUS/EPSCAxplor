"""Tests for src/routes/documents.py — GET /documents (#26)."""

from __future__ import annotations

import contextlib
import uuid
from datetime import date, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.config import Settings
from src.db.documents import DocumentRecord
from src.routes.documents import DocumentsResponse, list_documents_route


def _settings() -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="doc-test-secret",
    )


def _doc(**overrides: Any) -> DocumentRecord:
    base: dict[str, Any] = dict(
        id=uuid.uuid4(),
        union_name="IBEW",
        document_type="primary_ca",
        title="IBEW Generation 2025-2030 Collective Agreement",
        effective_date=date(2025, 5, 1),
        expiry_date=date(2030, 4, 30),
        is_expired=False,
        chunk_count=312,
        ingested_at=datetime(2026, 4, 15),
    )
    base.update(overrides)
    return DocumentRecord(**base)


@contextlib.asynccontextmanager
async def _fake_connect(*_a: object, **_k: object) -> Any:
    yield AsyncMock()


async def test_lists_documents_with_total() -> None:
    docs = [_doc(), _doc(union_name="Sheet Metal Workers", title="SMW CA")]
    with patch("src.routes.documents.connect", _fake_connect), patch(
        "src.routes.documents.list_documents", new=AsyncMock(return_value=docs)
    ):
        resp = await list_documents_route(
            settings=_settings(), union_name=None, document_type=None, is_expired=None
        )
    assert isinstance(resp, DocumentsResponse)
    assert resp.total == 2
    assert resp.documents[0].union_name == "IBEW"
    assert isinstance(resp.documents[0].id, str)


async def test_passes_filters_through() -> None:
    with patch("src.routes.documents.connect", _fake_connect), patch(
        "src.routes.documents.list_documents", new=AsyncMock(return_value=[])
    ) as listed:
        await list_documents_route(
            settings=_settings(),
            union_name="IBEW",
            document_type="primary_ca",
            is_expired=False,
        )
    assert listed.await_args.kwargs == {
        "union_name": "IBEW",
        "document_type": "primary_ca",
        "is_expired": False,
    }


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/documents").status_code == 401
