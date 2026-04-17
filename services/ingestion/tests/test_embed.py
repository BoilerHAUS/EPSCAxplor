"""Tests for embed.py — Stage 5 of the ingestion pipeline."""

from __future__ import annotations

import math
from chunk import Chunk
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from embed import EMBED_MODEL, embed_chunks

EMBED_DIM = 768


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_chunk(text: str, index: int = 0) -> Chunk:
    return Chunk(
        text=text,
        page_number=1,
        is_table=False,
        article_number="Article 1",
        section_number=None,
        article_title="Scope",
        chunk_index=index,
    )


def _fake_embedding() -> list[float]:
    return [0.1] * EMBED_DIM


def _mock_client(batches: list[list[list[float]]]) -> MagicMock:
    """
    Return a mock AsyncClient context manager whose .post() yields one response
    per call, each containing the embedding batch provided.
    """
    responses = []
    for batch_embeddings in batches:
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"embeddings": batch_embeddings}
        responses.append(resp)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=responses)
    return mock_client


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestEmbedEmpty:
    @pytest.mark.asyncio
    async def test_empty_chunks_returns_empty_list(self) -> None:
        result = await embed_chunks([])
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_chunks_makes_no_http_calls(self) -> None:
        mock_client = _mock_client([])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            await embed_chunks([])
        mock_client.post.assert_not_called()


class TestEmbedSingleBatch:
    @pytest.mark.asyncio
    async def test_single_chunk_returns_one_embedding(self) -> None:
        chunks = [_make_chunk("hello world")]
        mock_client = _mock_client([[_fake_embedding()]])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            result = await embed_chunks(chunks)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_embedding_has_correct_dimension(self) -> None:
        chunks = [_make_chunk("hello world")]
        mock_client = _mock_client([[_fake_embedding()]])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            result = await embed_chunks(chunks)
        assert len(result[0]) == EMBED_DIM

    @pytest.mark.asyncio
    async def test_three_chunks_single_batch_makes_one_call(self) -> None:
        chunks = [_make_chunk(f"text {i}", i) for i in range(3)]
        mock_client = _mock_client([[_fake_embedding()] * 3])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            result = await embed_chunks(chunks, batch_size=32)
        assert mock_client.post.call_count == 1
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_correct_model_sent_in_request(self) -> None:
        chunks = [_make_chunk("hello")]
        mock_client = _mock_client([[_fake_embedding()]])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            await embed_chunks(chunks)
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["model"] == EMBED_MODEL

    @pytest.mark.asyncio
    async def test_chunk_texts_sent_as_input(self) -> None:
        chunks = [_make_chunk("first text"), _make_chunk("second text", 1)]
        mock_client = _mock_client([[_fake_embedding(), _fake_embedding()]])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            await embed_chunks(chunks)
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["input"] == ["first text", "second text"]


class TestEmbedBatching:
    @pytest.mark.asyncio
    async def test_exact_batch_size_makes_one_call(self) -> None:
        n = 4
        chunks = [_make_chunk(f"t{i}", i) for i in range(n)]
        mock_client = _mock_client([[_fake_embedding()] * n])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            result = await embed_chunks(chunks, batch_size=4)
        assert mock_client.post.call_count == 1
        assert len(result) == n

    @pytest.mark.asyncio
    async def test_one_over_batch_size_makes_two_calls(self) -> None:
        n = 5
        chunks = [_make_chunk(f"t{i}", i) for i in range(n)]
        mock_client = _mock_client([
            [_fake_embedding()] * 4,
            [_fake_embedding()],
        ])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            result = await embed_chunks(chunks, batch_size=4)
        assert mock_client.post.call_count == 2
        assert len(result) == n

    @pytest.mark.asyncio
    async def test_batch_count_matches_ceil_division(self) -> None:
        n = 70
        batch_size = 32
        expected_calls = math.ceil(n / batch_size)
        chunks = [_make_chunk(f"t{i}", i) for i in range(n)]
        # Build response batches: first two full, last partial
        batches = []
        for start in range(0, n, batch_size):
            size = min(batch_size, n - start)
            batches.append([_fake_embedding()] * size)
        mock_client = _mock_client(batches)
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            result = await embed_chunks(chunks, batch_size=batch_size)
        assert mock_client.post.call_count == expected_calls
        assert len(result) == n

    @pytest.mark.asyncio
    async def test_embeddings_returned_in_chunk_order(self) -> None:
        """Embeddings must come back in the same order as input chunks."""
        n = 5
        chunks = [_make_chunk(f"t{i}", i) for i in range(n)]
        # Use distinct marker values to verify ordering
        ordered_embeddings = [[float(i)] * EMBED_DIM for i in range(n)]
        mock_client = _mock_client([
            ordered_embeddings[:4],
            ordered_embeddings[4:],
        ])
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            result = await embed_chunks(chunks, batch_size=4)
        for i, vec in enumerate(result):
            assert vec[0] == float(i), f"Chunk {i} embedding out of order"


class TestEmbedErrorPropagation:
    @pytest.mark.asyncio
    async def test_http_error_propagates(self) -> None:
        import httpx

        chunks = [_make_chunk("hello")]
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await embed_chunks(chunks)

    @pytest.mark.asyncio
    async def test_malformed_response_raises_value_error(self) -> None:
        """Ollama returning 200 with {'error': '...'} must raise ValueError, not KeyError."""
        chunks = [_make_chunk("hello")]
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"error": "model not found"}
        mock_client.post = AsyncMock(return_value=resp)
        with patch("embed.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="embeddings"):
                await embed_chunks(chunks)
