"""
Stage 2: Extract — extract raw text and tables from PDFs.

For each PDF in the corpus, extracts:
- Full text blocks per page, with 1-indexed page numbers preserved
- Structured table blocks per page, flagged with is_table=True

Output feeds into Stage 3 (classify.py) which assigns document metadata,
and Stage 4 (chunk.py) which applies structure-aware chunking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

_PAGE_COMMENT_RE = re.compile(r"<!--\s*page:\s*(\d+)\s*-->")
_TABLE_SEPARATOR_RE = re.compile(r"^\|[-| :]+\|$")

# Type alias for an immutable table (tuple-of-tuples preserves frozen semantics)
TableRows = tuple[tuple[str | None, ...], ...]


@dataclass(frozen=True)
class TextBlock:
    """A prose text block extracted from a single PDF page."""

    text: str
    page_number: int
    is_table: bool = False


@dataclass(frozen=True)
class TableBlock:
    """A structured table extracted from a single PDF page.

    `rows` is stored as a tuple-of-tuples so that frozen=True actually prevents
    mutation.  Downstream consumers iterate rows — they do not need mutability.
    """

    rows: TableRows
    page_number: int
    is_table: bool = True


@dataclass
class ExtractedDocument:
    """All content extracted from a single PDF file."""

    source_path: Path
    blocks: list[TextBlock | TableBlock] = field(default_factory=list)
    page_count: int = 0


def _to_table_rows(raw: list[list[str | None]]) -> TableRows:
    """Convert pdfplumber's list-of-lists into an immutable tuple-of-tuples."""
    return tuple(tuple(row) for row in raw)


def _parse_pipe_table(lines: list[str]) -> TableRows | None:
    """Parse a contiguous block of pipe-table lines into TableRows.

    Returns None if the block is not a valid pipe table (missing separator row).
    Separator row (e.g. |---|---|) is excluded from the returned rows.
    """
    if len(lines) < 2:
        return None

    sep_index = next(
        (i for i, ln in enumerate(lines) if _TABLE_SEPARATOR_RE.match(ln.strip())),
        None,
    )
    if sep_index is None:
        return None

    def _parse_row(line: str) -> tuple[str | None, ...]:
        stripped = line.strip().strip("|")
        return tuple(cell.strip() or None for cell in stripped.split("|"))

    rows: list[tuple[str | None, ...]] = []
    for i, line in enumerate(lines):
        if i == sep_index:
            continue
        rows.append(_parse_row(line))

    return tuple(rows)


def extract_markdown(md_path: Path, page_count: int) -> ExtractedDocument:
    """Extract text and table blocks from a Markdown file produced by convert.py.

    Page boundaries are detected via <!-- page: N --> comments. Tables are
    detected by pipe-delimiter syntax with a separator row; malformed tables
    fall back to TextBlock.

    Args:
        md_path:    Path to the .md file (output of convert_pdf).
        page_count: Total page count to set on the returned ExtractedDocument.

    Returns:
        ExtractedDocument with TextBlock and TableBlock entries.

    Raises:
        FileNotFoundError: If md_path does not exist.
    """
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    doc = ExtractedDocument(source_path=md_path, page_count=page_count)
    current_page = 1
    pending_text: list[str] = []
    pending_table: list[str] = []
    in_table = False

    def _flush_text() -> None:
        text = "\n".join(pending_text).strip()
        if text:
            doc.blocks.append(TextBlock(text=text, page_number=current_page))
        pending_text.clear()

    def _flush_table() -> None:
        parsed = _parse_pipe_table(pending_table)
        if parsed is not None:
            doc.blocks.append(TableBlock(rows=parsed, page_number=current_page))
        else:
            doc.blocks.append(
                TextBlock(text="\n".join(pending_table).strip(), page_number=current_page)
            )
        pending_table.clear()

    content = md_path.read_text(encoding="utf-8")

    for raw_line in content.splitlines():
        page_match = _PAGE_COMMENT_RE.match(raw_line.strip())
        if page_match:
            if in_table:
                _flush_table()
                in_table = False
            else:
                _flush_text()
            current_page = int(page_match.group(1))
            continue

        stripped = raw_line.strip()
        is_pipe_line = stripped.startswith("|") and stripped.endswith("|")
        is_header = stripped.startswith("##")

        if is_pipe_line:
            if not in_table:
                _flush_text()
                in_table = True
            pending_table.append(raw_line)
        elif is_header:
            if in_table:
                _flush_table()
                in_table = False
            else:
                _flush_text()
            pending_text.append(raw_line)
        else:
            if in_table:
                _flush_table()
                in_table = False
            pending_text.append(raw_line)

    if in_table:
        _flush_table()
    else:
        _flush_text()

    return doc


def extract_pdf(pdf_path: Path) -> ExtractedDocument:
    """
    Extract text and tables from a PDF file.

    Each page is processed independently. Text and table blocks carry the
    1-indexed page number as reported by pdfplumber. Empty or whitespace-only
    pages produce no text block.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        ExtractedDocument containing all text and table blocks with page numbers.

    Raises:
        FileNotFoundError: If pdf_path does not exist.
        ValueError:        If pdfplumber cannot parse the file (corrupt, encrypted,
                           or not a valid PDF).
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = ExtractedDocument(source_path=pdf_path)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            doc.page_count = len(pdf.pages)
            for page in pdf.pages:
                page_num: int = page.page_number  # pdfplumber is 1-indexed

                # Extract tables — each table is a list of rows, each row a list of cells
                raw_tables: list[list[list[str | None]]] = page.extract_tables()
                for table_data in raw_tables:
                    if table_data:
                        doc.blocks.append(
                            TableBlock(
                                rows=_to_table_rows(table_data),
                                page_number=page_num,
                            )
                        )

                # Extract full page text (may overlap with table regions — deduplication
                # is handled downstream in the chunk stage)
                raw_text: str | None = page.extract_text(x_tolerance=3, y_tolerance=3)
                text = (raw_text or "").strip()
                if text:
                    doc.blocks.append(TextBlock(text=text, page_number=page_num))
    except Exception as exc:
        # pdfminer (pdfplumber's parser) raises several exception types for corrupt,
        # truncated, or encrypted PDFs.  Convert to ValueError so callers get a
        # stable contract and can decide whether to skip or abort.
        raise ValueError(f"Failed to parse PDF {pdf_path}: {exc}") from exc

    return doc
