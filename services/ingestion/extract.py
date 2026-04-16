"""
Stage 2: Extract — extract raw text and tables from PDFs.

For each PDF in the corpus, extracts:
- Full text blocks per page, with 1-indexed page numbers preserved
- Structured table blocks per page, flagged with is_table=True

Output feeds into Stage 3 (classify.py) which assigns document metadata,
and Stage 4 (chunk.py) which applies structure-aware chunking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

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
