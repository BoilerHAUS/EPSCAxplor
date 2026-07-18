"""
Stage 4: Chunk — structure-aware chunking of classified documents.

Splits each ClassifiedDocument into Chunk objects following the rules defined
in planning.md §6:

1. Split at article boundaries (ARTICLE N — TITLE headings) first.
2. If an article exceeds the token limit, split at section boundaries (N.NN).
3. For sections still above the limit, apply token-count splitting with a
   50-token overlap — never mid-sentence.
4. TableBlock instances are kept atomic regardless of size.

Chunk metadata (article_number, section_number, article_title, page_number,
chunk_index, is_table) is attached at this stage and flows into the embed and
store stages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from classify import ClassifiedDocument
from extract import TableBlock, TableRows, TextBlock

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_CHUNK_TOKENS: int = 500
OVERLAP_TOKENS: int = 50
CHARS_PER_TOKEN: int = 4  # English-text approximation (~4 chars per token)

_MAX_CHARS = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN   # 2 000
_OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN  # 200

# When a table is emitted as its own chunk, prepend up to this many characters of
# its section's narrative so a terse table (e.g. a rate table whose own text never
# says "subsistence") stays retrievable by the terms that introduce it (#126).
# Sized to reach the naming term even when a long lead-in (e.g. a "regular
# residence" footnote) sits between the section heading and the term, and kept
# well under embed.py's MAX_EMBED_CHARS (2500) so the table's own rows still reach
# the embedding window.
_TABLE_LEAD_IN_CHARS: int = 1600

# ─── Regex patterns ───────────────────────────────────────────────────────────

# EPSCA article headings: "ARTICLE 12 — OVERTIME", "ARTICLE 3", "ARTICLE 1 – SCOPE"
# Accepts em-dash (—), en-dash (–), and plain hyphen (-) as separators.
_ARTICLE_RE = re.compile(
    r"^ARTICLE\s+(\d+)\s*(?:[—–-]\s*(.+))?$",
    re.IGNORECASE,
)

# Markdown H2/H3 headers used in wage schedule documents produced by convert.py
_MARKDOWN_HEADER_RE = re.compile(r"^#{2,3}\s+(.+)$")

# Section/clause numbers at the start of a line: "1.01", "12.03", "4.02a"
_SECTION_RE = re.compile(r"^(\d+\.\d+[a-z]?)\s")

# Sentence-ending punctuation followed by whitespace or end-of-string
_SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)")

# ─── Data structures ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Chunk:
    """A single chunk produced by the chunk stage, ready for embedding."""

    text: str
    page_number: int
    is_table: bool
    article_number: str | None
    section_number: str | None
    article_title: str | None
    chunk_index: int
    metadata: dict[str, object] | None = None


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _count_tokens(text: str) -> int:
    """Approximate token count using a 4-chars-per-token heuristic."""
    return len(text) // CHARS_PER_TOKEN


def _format_table(rows: TableRows) -> str:
    """Serialise table rows to pipe-delimited text for embedding."""
    lines: list[str] = []
    for row in rows:
        cells = [str(cell or "").strip() for cell in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _build_section_narrative(
    blocks: list[TextBlock | TableBlock],
) -> dict[tuple[str | None, str], str]:
    """Accumulate each numbered section's full narrative, keyed by
    ``(article_number, section_number)``.

    Built in a first pass over *all* text blocks so a table can inherit its
    section's naming text even when the extractor emits the TableBlock *before*
    the narrative that names it — pdfplumber does not guarantee reading order,
    so the immediately-preceding text is unreliable (issue #126).  Keying
    includes the article so a section number reused across articles (e.g. a
    restated appendix schedule) never blends narrative from the wrong article.
    """
    narrative: dict[tuple[str | None, str], list[str]] = {}
    current_article: str | None = None
    current_section: str | None = None
    for block in blocks:
        if not isinstance(block, TextBlock):
            continue
        for raw_line in block.text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            article_match = _ARTICLE_RE.match(line)
            if article_match:
                current_article = f"Article {article_match.group(1)}"
                current_section = None
                continue
            section_match = _SECTION_RE.match(line)
            if section_match:
                current_section = section_match.group(1)
            if current_section is not None:
                narrative.setdefault((current_article, current_section), []).append(line)
    return {key: "\n".join(lines) for key, lines in narrative.items()}


def _table_section_key(rows: TableRows, current_section: str | None) -> str | None:
    """Return the section a table belongs to.

    Prefers a section number embedded in the table's own leading (header) cell
    (e.g. ``"26.2 Room and Board Rates"``); falls back to the section in effect
    where the table appears.  Only the first row is inspected, so a blank header
    corner does not let a look-alike data cell (e.g. ``"2025.05"``) be mistaken
    for a section number.
    """
    if rows:
        for cell in rows[0]:
            text = str(cell).strip() if cell else ""
            if text:
                match = _SECTION_RE.match(text)
                return match.group(1) if match else current_section
    return current_section


def _find_sentence_boundary(text: str, near: int) -> int:
    """
    Return the index just after the last sentence-ending punctuation at or
    before `near`.  Falls back to the last whitespace, then to `near` itself.
    """
    # Search backward up to 300 chars from `near`
    search_start = max(0, near - 300)
    segment = text[search_start:near]

    # Find the last sentence-ending match in the segment
    last_match: re.Match[str] | None = None
    for m in _SENTENCE_END_RE.finditer(segment):
        last_match = m

    if last_match is not None:
        return search_start + last_match.end()

    # Fall back to last whitespace
    for i in range(near, max(search_start, 0), -1):
        if text[i - 1] == " ":
            return i

    return near  # Last resort: split at `near` exactly


def _split_with_overlap(
    text: str,
    page_number: int,
    article_number: str | None,
    article_title: str | None,
    section_number: str | None,
) -> list[Chunk]:
    """
    Split oversized section text into chunks of ≤ MAX_CHUNK_TOKENS with a
    50-token overlap between consecutive chunks.  Splits are made at sentence
    boundaries where possible, never mid-sentence.
    """
    raw: list[Chunk] = []
    remaining = text

    while len(remaining) > _MAX_CHARS:
        split_pos = _find_sentence_boundary(remaining, _MAX_CHARS)

        # Guard against degenerate cases (no boundary found near the limit)
        if split_pos <= 0:
            split_pos = _MAX_CHARS

        chunk_text = remaining[:split_pos].strip()
        if chunk_text:
            raw.append(
                Chunk(
                    text=chunk_text,
                    page_number=page_number,
                    is_table=False,
                    article_number=article_number,
                    section_number=section_number,
                    article_title=article_title,
                    chunk_index=0,  # reassigned in chunk_document
                )
            )

        # Overlap: next chunk starts 50 tokens before the split point
        overlap_start = max(0, split_pos - _OVERLAP_CHARS)
        # Advance to the next word boundary so the overlap starts cleanly
        while overlap_start < split_pos and remaining[overlap_start] not in (" ", "\n"):
            overlap_start += 1
        overlap_start = min(overlap_start + 1, split_pos)

        next_remaining = remaining[overlap_start:].lstrip()

        # Safety: if the candidate next_remaining made no progress (e.g. the
        # word-boundary walk saturated at split_pos), advance past split_pos
        # to avoid silently dropping content.
        if len(next_remaining) >= len(remaining):
            remaining = remaining[split_pos:].lstrip()
        else:
            remaining = next_remaining

    if remaining.strip():
        raw.append(
            Chunk(
                text=remaining.strip(),
                page_number=page_number,
                is_table=False,
                article_number=article_number,
                section_number=section_number,
                article_title=article_title,
                chunk_index=0,
            )
        )

    return raw


def _split_into_sections(
    lines: list[tuple[str, int]],
) -> list[tuple[str | None, list[tuple[str, int]]]]:
    """
    Group article lines by section number.

    Returns a list of (section_number, lines) pairs.  Lines before the first
    section number are grouped under section_number=None (the article preamble /
    heading itself).
    """
    groups: list[tuple[str | None, list[tuple[str, int]]]] = []
    current_section: str | None = None
    current_lines: list[tuple[str, int]] = []

    for line, page in lines:
        match = _SECTION_RE.match(line)
        if match:
            if current_lines:
                groups.append((current_section, current_lines))
            current_section = match.group(1)
            current_lines = [(line, page)]
        else:
            current_lines.append((line, page))

    if current_lines:
        groups.append((current_section, current_lines))

    return groups


def _process_article(
    lines: list[tuple[str, int]],
    article_number: str | None,
    article_title: str | None,
    out: list[Chunk],
) -> None:
    """
    Convert accumulated article lines into one or more Chunks and append to
    `out`.

    Strategy:
    - If the full article text fits within MAX_CHUNK_TOKENS → one chunk.
    - Otherwise split at section boundaries; apply token-count fallback with
      overlap for any section that still exceeds the limit.
    """
    if not lines:
        return

    full_text = "\n".join(line for line, _ in lines).strip()
    if not full_text:
        return

    page_number = lines[0][1]

    # ── Fast path: entire article fits in one chunk ───────────────────────────
    if _count_tokens(full_text) <= MAX_CHUNK_TOKENS:
        out.append(
            Chunk(
                text=full_text,
                page_number=page_number,
                is_table=False,
                article_number=article_number,
                section_number=None,
                article_title=article_title,
                chunk_index=0,
            )
        )
        return

    # ── Split at section boundaries ───────────────────────────────────────────
    sections = _split_into_sections(lines)

    for section_number, section_lines in sections:
        section_text = "\n".join(line for line, _ in section_lines).strip()
        if not section_text:
            continue

        s_page = section_lines[0][1]

        if _count_tokens(section_text) <= MAX_CHUNK_TOKENS:
            out.append(
                Chunk(
                    text=section_text,
                    page_number=s_page,
                    is_table=False,
                    article_number=article_number,
                    section_number=section_number,
                    article_title=article_title,
                    chunk_index=0,
                )
            )
        else:
            # Token-count fallback with overlap
            out.extend(
                _split_with_overlap(
                    text=section_text,
                    page_number=s_page,
                    article_number=article_number,
                    article_title=article_title,
                    section_number=section_number,
                )
            )


def _process_wage_schedule(
    blocks: list[TextBlock | TableBlock],
    out: list[Chunk],
) -> None:
    """Chunk a wage schedule document using markdown H2/H3 headers as boundaries.

    Text blocks containing ## or ### headers are split at those boundaries.
    TableBlocks are kept atomic and inherit the most recent header as article_title.
    """
    current_title: str | None = None
    current_lines: list[tuple[str, int]] = []

    def _flush_section() -> None:
        text = "\n".join(line for line, _ in current_lines).strip()
        if not text:
            return
        page = current_lines[0][1]
        if _count_tokens(text) <= MAX_CHUNK_TOKENS:
            out.append(
                Chunk(
                    text=text,
                    page_number=page,
                    is_table=False,
                    article_number=None,
                    section_number=None,
                    article_title=current_title,
                    chunk_index=0,
                )
            )
        else:
            out.extend(
                _split_with_overlap(
                    text=text,
                    page_number=page,
                    article_number=None,
                    article_title=current_title,
                    section_number=None,
                )
            )
        current_lines.clear()

    for block in blocks:
        if isinstance(block, TableBlock):
            _flush_section()
            table_text = _format_table(block.rows)
            out.append(
                Chunk(
                    text=table_text,
                    page_number=block.page_number,
                    is_table=True,
                    article_number=None,
                    section_number=None,
                    article_title=current_title,
                    chunk_index=0,
                )
            )
        elif isinstance(block, TextBlock):
            for raw_line in block.text.split("\n"):
                header_match = _MARKDOWN_HEADER_RE.match(raw_line.strip())
                if header_match:
                    _flush_section()
                    current_title = header_match.group(1).strip()
                else:
                    stripped = raw_line.strip()
                    if stripped:
                        current_lines.append((stripped, block.page_number))

    _flush_section()


# ─── Public API ───────────────────────────────────────────────────────────────


def chunk_document(doc: ClassifiedDocument) -> list[Chunk]:
    """
    Split a ClassifiedDocument into structure-aware Chunks.

    Processing order mirrors the block order from extract.py:
    - TableBlocks → one atomic Chunk each (is_table=True).
    - TextBlocks  → accumulated per-article, then split as described above.

    Chunk indices are assigned sequentially after all chunks are collected.

    Args:
        doc: A ClassifiedDocument produced by classify.py.

    Returns:
        A list of Chunks in document order with sequential chunk_index values.
    """
    raw: list[Chunk] = []

    if doc.metadata.document_type == "wage_schedule":
        _process_wage_schedule(doc.extracted.blocks, raw)
        return [replace(c, chunk_index=i) for i, c in enumerate(raw)]

    # First pass: collect each section's full narrative so a table can inherit
    # the terms that name it regardless of the extractor's block ordering (#126).
    section_narrative = _build_section_narrative(doc.extracted.blocks)

    # Running article/section context shared between text and table blocks
    current_article_number: str | None = None
    current_article_title: str | None = None
    current_section_number: str | None = None

    # Lines accumulated for the current article: (text, page_number)
    article_lines: list[tuple[str, int]] = []

    def _flush() -> None:
        nonlocal article_lines
        _process_article(article_lines, current_article_number, current_article_title, raw)
        article_lines = []  # replace, never mutate

    for block in doc.extracted.blocks:
        if isinstance(block, TableBlock):
            # Prepend the table's section narrative so a terse table (whose own
            # text may never name what it lists — e.g. a rate table headed "Room
            # and Board Rates" that users query as "subsistence allowance") stays
            # retrievable, and inherit that section's number for citation (#126).
            _flush()
            table_text = _format_table(block.rows)
            section = _table_section_key(block.rows, current_section_number)
            lead_in = (
                section_narrative.get((current_article_number, section), "")[
                    :_TABLE_LEAD_IN_CHARS
                ].strip()
                if section is not None
                else ""
            )
            raw.append(
                Chunk(
                    text=f"{lead_in}\n\n{table_text}" if lead_in else table_text,
                    page_number=block.page_number,
                    is_table=True,
                    article_number=current_article_number,
                    article_title=current_article_title,
                    section_number=section,
                    chunk_index=0,
                )
            )

        elif isinstance(block, TextBlock):
            for raw_line in block.text.split("\n"):
                line = raw_line.strip()
                if not line:
                    continue

                article_match = _ARTICLE_RE.match(line)
                if article_match:
                    # Flush the previous article before starting the new one
                    _flush()
                    num_str = article_match.group(1)
                    current_article_number = f"Article {num_str}"
                    title = article_match.group(2)
                    current_article_title = title.strip() if title else None
                    current_section_number = None
                else:
                    section_match = _SECTION_RE.match(line)
                    if section_match:
                        current_section_number = section_match.group(1)

                # Always add the line (including the heading itself) so the
                # heading text appears at the top of the first chunk for context
                article_lines.append((line, block.page_number))

    # Flush the final article
    _flush()

    # Assign sequential chunk_index values (Chunk is frozen, so rebuild)
    return [replace(c, chunk_index=i) for i, c in enumerate(raw)]
