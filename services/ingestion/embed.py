"""
Stage 5: Embed — generate 768-dimensional embeddings for chunks via Ollama.

Calls Ollama's /api/embed endpoint (batch-capable) using the nomic-embed-text
model.  Chunks are sent in batches of BATCH_SIZE to bound per-request payload
size.  The caller receives embeddings in the same order as the input chunks.

Environment variables:
    OLLAMA_BASE_URL: Base URL for the Ollama instance.
                     Default: http://127.0.0.1:11434
"""

from __future__ import annotations

import os
from chunk import Chunk

import httpx

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
EMBED_MODEL: str = "nomic-embed-text"
BATCH_SIZE: int = 32


async def embed_chunks(
    chunks: list[Chunk],
    *,
    base_url: str = OLLAMA_BASE_URL,
    batch_size: int = BATCH_SIZE,
) -> list[list[float]]:
    """
    Generate embeddings for a list of chunks using Ollama's nomic-embed-text model.

    Sends chunks in batches of `batch_size` to Ollama's /api/embed endpoint.
    Each embedding is a list of 768 floats.

    Args:
        chunks:     Chunks produced by chunk_document().
        base_url:   Ollama base URL. Defaults to OLLAMA_BASE_URL env var.
        batch_size: Number of texts per HTTP request. Defaults to BATCH_SIZE.

    Returns:
        List of embedding vectors in the same order as `chunks`.

    Raises:
        httpx.HTTPStatusError: If Ollama returns a non-2xx response.
        httpx.RequestError:    If the request cannot be sent (connection refused, etc.).
    """
    if not chunks:
        return []

    texts = [c.text for c in chunks]
    embeddings: list[list[float]] = []

    async with httpx.AsyncClient(base_url=base_url, timeout=120.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await client.post(
                "/api/embed",
                json={"model": EMBED_MODEL, "input": batch},
            )
            response.raise_for_status()
            data = response.json()
            if "embeddings" not in data:
                raise ValueError(
                    f"Ollama response missing 'embeddings' key; "
                    f"got: {list(data.keys())}"
                )
            embeddings.extend(data["embeddings"])

    return embeddings
