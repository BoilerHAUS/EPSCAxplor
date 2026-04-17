"""Citation extraction — Step 5b of the EPSCAxplor query pipeline.

Parses [SOURCE N] markers from the generated answer and maps each to
the corresponding retrieved chunk, producing structured CitationRef objects.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from src.rag.retrieval import ChunkResult

_SOURCE_PATTERN: re.Pattern[str] = re.compile(r"\[SOURCE\s+(\d+)\]", re.IGNORECASE)


class CitationRef(BaseModel):
    source_number: int
    union_name: str
    document_title: str
    document_type: str
    effective_date: str | None
    article: str | None
    section: str | None
    article_title: str | None
    page_number: int | None
    excerpt: str


def extract_citations(
    answer: str,
    chunks: list[ChunkResult],
    title_map: dict[str, str] | None = None,
) -> list[CitationRef]:
    """Extract structured citations from an answer referencing retrieved chunks.

    Finds all [SOURCE N] patterns in *answer* and maps each to the chunk at
    index N-1.  References to out-of-range indices are silently ignored.
    Duplicate source numbers are deduplicated; results are sorted ascending
    by source_number.

    Args:
        answer: Generated text from Claude containing [SOURCE N] markers.
        chunks: Chunks in the same order passed to assemble_context() (1-indexed).
        title_map: Optional document_id → human-readable title mapping.

    Returns:
        List of CitationRef objects, one per unique referenced source.
    """
    resolved: dict[str, str] = title_map or {}
    seen: set[int] = set()
    citations: list[CitationRef] = []

    for match in _SOURCE_PATTERN.finditer(answer):
        n = int(match.group(1))
        if n in seen or n < 1 or n > len(chunks):
            continue
        seen.add(n)
        chunk = chunks[n - 1]
        title = resolved.get(chunk.document_id) or chunk.source_filename
        citations.append(
            CitationRef(
                source_number=n,
                union_name=chunk.union_name,
                document_title=title,
                document_type=chunk.document_type,
                effective_date=chunk.effective_date,
                article=chunk.article_number,
                section=chunk.section_number,
                article_title=chunk.article_title,
                page_number=chunk.page_number,
                excerpt=chunk.text,
            )
        )

    citations.sort(key=lambda c: c.source_number)
    return citations
