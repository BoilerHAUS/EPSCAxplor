"""Tests for the best-effort _write_query_log wrapper in routes/query.py (#88)."""

from __future__ import annotations

import contextlib
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

from src.routes.query import _write_query_log


@contextlib.asynccontextmanager
async def _fake_connect(*_a: object, **_k: object) -> Any:
    yield AsyncMock()


def _kwargs() -> dict[str, Any]:
    return dict(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        query_text="q",
        response_text="r",
        model_used="claude-haiku-4-5-20251001",
        union_filter=["IBEW"],
        doc_type_filter=["primary_ca"],
        chunks_retrieved=6,
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=250,
        citations=[{"source_number": 1}],
    )


async def test_wrapper_returns_str_id_on_success() -> None:
    new_id = uuid.uuid4()
    with patch("src.routes.query.connect", _fake_connect), patch(
        "src.routes.query.insert_query_log", new=AsyncMock(return_value=new_id)
    ):
        result = await _write_query_log("postgresql://x", **_kwargs())
    assert result == str(new_id)


async def test_wrapper_returns_none_and_swallows_errors() -> None:
    with patch("src.routes.query.connect", _fake_connect), patch(
        "src.routes.query.insert_query_log",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        result = await _write_query_log("postgresql://x", **_kwargs())
    assert result is None
