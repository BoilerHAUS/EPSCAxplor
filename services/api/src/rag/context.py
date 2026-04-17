"""Context assembly for the EPSCAxplor RAG pipeline.

Step 3 of the query pipeline: format retrieved chunks into a numbered
[SOURCE N] block that Claude can reference in its response.

Design note — title resolution
-------------------------------
``title`` is absent from the Qdrant payload (store.py never writes it).
``assemble_context`` accepts an optional ``title_map`` argument that maps
``document_id`` (UUID string) → human-readable title sourced from the
PostgreSQL ``documents.title`` column.  When ``title_map`` is not supplied,
or when a chunk's ``document_id`` is not present in the map, the chunk's
``source_filename`` is used as a fallback.  Callers that require the
canonical title should execute a single batch DB query (one
``WHERE id = ANY(...)`` call) and pass the result as ``title_map``.
"""

from __future__ import annotations

from datetime import date

from src.rag.retrieval import ChunkResult

# Human-readable labels for each document_type code used in citation headers.
_DOC_TYPE_LABELS: dict[str, str] = {
    "primary_ca": "Primary Collective Agreement",
    "nuclear_pa": "Nuclear Project Agreement",
    "moa_supplement": "MOA / Supplementary Agreement",
    "wage_schedule": "Wage Schedule",
}


def _format_date(iso: str | None) -> str:
    """Convert an ISO date string (YYYY-MM-DD) to a human-readable form.

    Returns an empty string for ``None`` or unparseable input so callers can
    safely use truthiness to decide whether to include the value.

    Examples:
        "2025-05-01" → "May 1, 2025"
        "2030-04-30" → "April 30, 2030"
        None         → ""
    """
    if not iso:
        return ""
    try:
        d = date.fromisoformat(iso)
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    except ValueError:
        return iso


def _resolve_title(chunk: ChunkResult, title_map: dict[str, str]) -> str:
    """Return the document title from *title_map*, falling back to source_filename."""
    return title_map.get(chunk.document_id) or chunk.source_filename


def assemble_context(
    chunks: list[ChunkResult],
    title_map: dict[str, str] | None = None,
) -> str:
    """Format retrieved chunks into a numbered source block for Claude.

    Each chunk is wrapped in a citation header matching the spec in
    docs/planning.md §7 Step 3::

        [SOURCE 1]
        Union: IBEW
        Document: IBEW Generation 2025-2030 Collective Agreement
        Document Type: Primary Collective Agreement
        Effective: May 1, 2025 | Expires: April 30, 2030
        Article 12 — Overtime | Section 12.03
        Page: 34

        "[chunk text here]"

    Lines are omitted entirely when the underlying field is absent (e.g. no
    article number, no page number) rather than emitting empty labels.

    Args:
        chunks: Retrieved chunks from Qdrant, ordered by descending score.
            Numbering begins at 1 and corresponds to the ``[SOURCE N]``
            references Claude is instructed to use.
        title_map: Optional mapping from ``document_id`` (UUID string) to the
            human-readable document title from ``documents.title`` in
            PostgreSQL.  When ``None`` or when a chunk's ID is absent from the
            map, ``source_filename`` is used as the document label.

    Returns:
        A multi-line string containing all source blocks, separated by
        ``\\n\\n---\\n\\n``, ready to append to the Claude system prompt after
        "Provided sources follow."
    """
    resolved: dict[str, str] = title_map or {}
    blocks: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        title = _resolve_title(chunk, resolved)
        doc_type_label = _DOC_TYPE_LABELS.get(chunk.document_type, chunk.document_type)

        # "Effective: May 1, 2025 | Expires: April 30, 2030"
        eff = _format_date(chunk.effective_date)
        exp = _format_date(chunk.expiry_date)
        date_parts: list[str] = []
        if eff:
            date_parts.append(f"Effective: {eff}")
        if exp:
            date_parts.append(f"Expires: {exp}")
        date_line = " | ".join(date_parts)

        # "Article 12 — Overtime | Section 12.03"
        article_parts: list[str] = []
        if chunk.article_number:
            part = chunk.article_number
            if chunk.article_title:
                part += f" — {chunk.article_title}"
            article_parts.append(part)
        if chunk.section_number:
            article_parts.append(f"Section {chunk.section_number}")
        article_line = " | ".join(article_parts)

        lines: list[str] = [f"[SOURCE {i}]"]
        lines.append(f"Union: {chunk.union_name}")
        lines.append(f"Document: {title}")
        lines.append(f"Document Type: {doc_type_label}")
        if date_line:
            lines.append(date_line)
        if article_line:
            lines.append(article_line)
        if chunk.page_number is not None:
            lines.append(f"Page: {chunk.page_number}")
        lines.append("")
        lines.append(f'"{chunk.text}"')

        blocks.append("\n".join(lines))

    return "\n\n---\n\n".join(blocks)
