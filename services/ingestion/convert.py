"""
Stage 1b: Convert — PDF to Markdown pre-processing.

Converts each PDF to structured Markdown before chunking, preserving table
structure (pipe-delimited rows) that pdfplumber's naive text extraction destroys.
Critical for wage schedule PDFs which are primarily tables.

Engines, selected per document by the manifest's ``conversion_engine`` field:

* ``pymupdf4llm`` (default) — general-purpose Markdown conversion.
* ``pdfplumber_columns`` — side-by-side two-column forms, where reading in
  visual line order interleaves the columns and destroys the association the
  form states (see the layout notes below).

Converted .md files are cached on disk keyed by source SHA-256 so re-running
the pipeline skips already-converted documents.

Cache layout (gitignored):
  corpus_md/<pdf_stem>.md
  corpus_md/<pdf_stem>.md.meta.json
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SUPPORTED_ENGINES = frozenset({"pymupdf4llm", "pdfplumber_columns"})
_PAGE_NUM_RE = re.compile(r"<!--\s*page:\s*(\d+)\s*-->")

# ─── Two-column form layout (#179) ────────────────────────────────────────────
#
# EPSCA publishes administrative forms — the Teamsters "Union Dues" sheet is the
# first in the corpus — laid out as side-by-side cards.  Every extractor that
# reads such a page in visual line order interleaves the columns:
#
#     Teamsters Local 230 Teamsters Local 879
#     2.5x the hourly rate plus $7.00 assessment 3x the hourly rate
#
# which destroys the local→formula association the document exists to state.  A
# model reading that will confidently pair local 879 with the $7.00 figure.  The
# `pdfplumber_columns` engine rebuilds the columns from word coordinates so each
# card is emitted whole, then re-attaches full-width tables in page order.

# A blank horizontal run at least this wide (PDF points) separates columns
# rather than words.  Roughly eight space widths at the 10pt body size these
# forms use, so ordinary and justified inter-word spacing never reaches it.
_MIN_GUTTER_PT = 24.0
# Words whose tops are within this many points of the line's FIRST word belong
# to that line.  Extractors report a line's words with ~1pt of jitter; lines are
# ~9pt apart.  Anchoring on the first word rather than the previous one is
# deliberate: a rolling anchor would let a line creep downward without bound
# across a run of slightly-drifting words.  These are digitally generated forms
# with flat baselines; a scanned or OCR'd source would want the rolling form.
_LINE_TOLERANCE_PT = 3.0
# A band is only serialised as columns when at least this many of its lines
# carried a gutter of their own.  One spaced-out line (the "MAP CODE:  ISSUED:
# REVISED:" form header) is alignment, not a column layout.
_MIN_COLUMN_LINES = 2


@dataclass(frozen=True)
class ConvertedDocument:
    """Result of converting a PDF to Markdown."""

    source_path: Path
    markdown_path: Path
    markdown: str
    engine: str
    engine_version: str
    page_count: int
    source_sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _convert_with_pymupdf4llm(pdf_path: Path) -> str:
    """Convert PDF to Markdown using pymupdf4llm.

    Returns the full markdown string with <!-- page: N --> boundary comments.
    """
    import pymupdf4llm  # type: ignore[import]

    chunks: list[dict] = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)

    pages_md: list[str] = []
    for chunk in chunks:
        # pymupdf4llm metadata["page"] is already 1-indexed
        page_num = chunk.get("metadata", {}).get("page", 1)
        pages_md.append(f"<!-- page: {page_num} -->\n{chunk['text']}")

    return "\n\n".join(pages_md)


@dataclass(frozen=True)
class _Word:
    """A word box: horizontal extent plus its text."""

    x0: float
    x1: float
    text: str


@dataclass(frozen=True)
class _Line:
    """Words sharing a visual baseline, ordered left to right."""

    top: float
    words: tuple[_Word, ...]

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)

    @property
    def x0(self) -> float:
        return self.words[0].x0

    @property
    def x1(self) -> float:
        return max(word.x1 for word in self.words)


def _group_words_into_lines(words: Iterable[Mapping[str, Any]]) -> list[_Line]:
    """Group pdfplumber word boxes into visual lines, top-down then left-right."""
    lines: list[_Line] = []
    pending: list[_Word] = []
    pending_top = 0.0

    def _flush() -> None:
        if pending:
            ordered = tuple(sorted(pending, key=lambda word: word.x0))
            lines.append(_Line(top=pending_top, words=ordered))

    for word in sorted(words, key=lambda w: (float(w["top"]), float(w["x0"]))):
        top = float(word["top"])
        if pending and top - pending_top > _LINE_TOLERANCE_PT:
            _flush()
            pending = []  # replace, never mutate the flushed list
        if not pending:
            pending_top = top
        pending.append(
            _Word(x0=float(word["x0"]), x1=float(word["x1"]), text=str(word["text"]))
        )

    _flush()
    return lines


def _line_gutters(line: _Line) -> list[tuple[float, float]]:
    """Blank horizontal runs in *line* wide enough to separate columns."""
    return [
        (left.x1, right.x0)
        for left, right in zip(line.words, line.words[1:], strict=False)
        if right.x0 - left.x1 >= _MIN_GUTTER_PT
    ]


def _widest(gutters: Sequence[tuple[float, float]]) -> tuple[float, float] | None:
    """The widest gutter, or None when there is none."""
    return max(gutters, key=lambda g: g[1] - g[0], default=None)


def _narrow(
    gutter: tuple[float, float], candidates: Sequence[tuple[float, float]]
) -> tuple[float, float] | None:
    """Intersect *gutter* with *candidates*, returning the widest overlap.

    A band's gutter narrows as more lines join it, converging on the blank
    corridor every line in the band agrees on.
    """
    overlaps = [
        (max(gutter[0], other[0]), min(gutter[1], other[1]))
        for other in candidates
        if max(gutter[0], other[0]) < min(gutter[1], other[1])
    ]
    return _widest(overlaps)


def _render_band(
    band: Sequence[_Line], gutter: tuple[float, float] | None, gutter_lines: int
) -> str:
    """Serialise a band: one column after the other, or verbatim if not columnar."""
    if gutter is None or gutter_lines < _MIN_COLUMN_LINES:
        return "\n".join(line.text for line in band)

    # A word starts either before the corridor or after it — never inside, since
    # the corridor is the blank run the band's lines agree on.
    left: list[str] = []
    right: list[str] = []
    for line in band:
        for column, words in (
            (left, [w for w in line.words if w.x0 < gutter[1]]),
            (right, [w for w in line.words if w.x0 >= gutter[1]]),
        ):
            if words:
                column.append(" ".join(word.text for word in words))
    return "\n\n".join("\n".join(column) for column in (left, right) if column)


def _column_segments(lines: Sequence[_Line]) -> list[str]:
    """Split *lines* into bands and serialise each one in reading order.

    Consecutive lines that agree on a blank corridor form a two-column band and
    are emitted column by column.  A line with no gutter of its own extends an
    open band when it sits entirely on one side of the corridor (a trailing
    phone number under the left card); a line that crosses the corridor is
    full-width and closes the band.
    """
    segments: list[str] = []
    band: list[_Line] = []
    gutter: tuple[float, float] | None = None
    gutter_lines = 0

    def _flush() -> None:
        if band:
            segments.append(_render_band(band, gutter, gutter_lines))

    for line in lines:
        own = _line_gutters(line)
        if gutter is None:
            if own:
                # A column layout starts here: emit the plain lines above it
                # first so prose is never folded into a column.
                _flush()
                band, gutter, gutter_lines = [line], _widest(own), 1
            else:
                band = [*band, line]
            continue

        narrowed = _narrow(gutter, own)
        if narrowed is not None:
            band, gutter, gutter_lines = [*band, line], narrowed, gutter_lines + 1
        elif line.x1 <= gutter[0] or line.x0 >= gutter[1]:
            band = [*band, line]
        else:
            _flush()
            band, gutter, gutter_lines = [line], _widest(own), 1 if own else 0

    _flush()
    return segments


def _table_markdown(rows: Sequence[Sequence[str | None]]) -> str:
    """Render extracted table rows as a pipe table extract.py can parse.

    Cell whitespace is collapsed so every row stays on ONE physical line:
    extract_markdown ends a table at the first line that does not start with a
    pipe, so a cell holding a hard newline would truncate the table and orphan
    the rest of its rows as loose text.

    Rows are padded and truncated to the header's width.  Merged or spanned
    cells make ``table.extract()`` return ragged rows, and neither this file's
    reader (``extract._parse_pipe_table``) nor ``chunk._format_table``
    validates cell counts — so a short row would silently shift every later
    value one column left, under the wrong heading.
    """
    if not rows:
        return ""
    width = len(rows[0])

    def _row(cells: Sequence[str | None]) -> str:
        padded = [*cells, *([None] * (width - len(cells)))][:width]
        joined = "|".join(" ".join((cell or "").split()).replace("|", r"\|") for cell in padded)
        return f"|{joined}|"

    separator = "|" + "|".join("---" for _ in rows[0]) + "|"
    return "\n".join([_row(rows[0]), separator, *(_row(row) for row in rows[1:])])


def _page_markdown(page: Any) -> str:
    """Convert one pdfplumber page: column-split text, tables in page order.

    Words inside a table's vertical span are left to that table's own markdown,
    so ``consumed_to`` walks down the page and never rewinds.  ``find_tables()``
    can return a table nested inside another on ruled or borderless layouts; the
    nested one is emitted but does not re-anchor the boundary, because rewinding
    would both drop the enclosing table's words above it and re-emit the ones
    below it as loose body text — the same rows in two places, one uncited.
    """
    tables = sorted(page.find_tables(), key=lambda table: table.bbox[1])
    words = page.extract_words()
    parts: list[str] = []
    consumed_to = 0.0

    for table in tables:
        top, bottom = float(table.bbox[1]), float(table.bbox[3])
        above = (
            []
            if top < consumed_to
            else [w for w in words if consumed_to <= float(w["top"]) < top]
        )
        parts = [
            *parts,
            *_column_segments(_group_words_into_lines(above)),
            _table_markdown(table.extract()),
        ]
        consumed_to = max(consumed_to, bottom)

    trailing = [w for w in words if float(w["top"]) >= consumed_to]
    parts = [*parts, *_column_segments(_group_words_into_lines(trailing))]
    return "\n\n".join(part for part in parts if part.strip())


def _convert_with_columns(pdf_path: Path) -> str:
    """Convert a two-column form PDF to Markdown, one column at a time.

    Returns the full markdown string with <!-- page: N --> boundary comments,
    matching the contract extract.extract_markdown expects.
    """
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        pages_md = [
            f"<!-- page: {page.page_number} -->\n{_page_markdown(page)}" for page in pdf.pages
        ]
    return "\n\n".join(pages_md)


def convert_pdf(
    pdf_path: Path,
    md_cache_dir: Path,
    engine: str = "pymupdf4llm",
    force: bool = False,
) -> ConvertedDocument:
    """Convert a PDF to Markdown, using a disk cache to avoid re-conversion.

    Args:
        pdf_path:     Absolute path to the source PDF.
        md_cache_dir: Directory where cached .md and .meta.json files are stored.
        engine:       Conversion backend — "pymupdf4llm" (default) or
                      "pdfplumber_columns" for side-by-side two-column forms.
        force:        If True, re-convert even when a valid cache entry exists.

    Returns:
        ConvertedDocument with markdown text, paths, and metadata.

    Raises:
        FileNotFoundError: If pdf_path does not exist.
        ValueError:        If engine is not supported.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if engine not in _SUPPORTED_ENGINES:
        raise ValueError(f"Unknown engine '{engine}'. Supported: {sorted(_SUPPORTED_ENGINES)}")

    md_cache_dir.mkdir(parents=True, exist_ok=True)

    md_path = md_cache_dir / (pdf_path.stem + ".md")
    sidecar = md_cache_dir / (pdf_path.stem + ".md.meta.json")

    source_sha = _sha256(pdf_path)

    if not force and md_path.exists() and sidecar.exists():
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            if meta.get("source_sha256") == source_sha:
                cached_md = md_path.read_text(encoding="utf-8")
                return ConvertedDocument(
                    source_path=pdf_path,
                    markdown_path=md_path,
                    markdown=cached_md,
                    engine=meta["engine"],
                    engine_version=meta["engine_version"],
                    page_count=meta.get("page_count", 0),
                    source_sha256=source_sha,
                )
        except (json.JSONDecodeError, KeyError):
            pass

    if engine == "pymupdf4llm":
        markdown_text = _convert_with_pymupdf4llm(pdf_path)
        try:
            import pymupdf4llm  # type: ignore[import]

            engine_version: str = getattr(pymupdf4llm, "__version__", "unknown")
        except ImportError:
            engine_version = "unknown"
    elif engine == "pdfplumber_columns":
        markdown_text = _convert_with_columns(pdf_path)
        try:
            import pdfplumber

            engine_version = getattr(pdfplumber, "__version__", "unknown")
        except ImportError:
            engine_version = "unknown"
    else:
        raise ValueError(f"Unknown engine '{engine}'")

    page_nums = [int(m.group(1)) for m in _PAGE_NUM_RE.finditer(markdown_text)]
    page_count = max(page_nums) if page_nums else 0

    tmp_md = md_path.with_suffix(".md.tmp")
    tmp_md.write_text(markdown_text, encoding="utf-8")
    tmp_md.rename(md_path)

    meta_payload = {
        "source_sha256": source_sha,
        "engine": engine,
        "engine_version": engine_version,
        "page_count": page_count,
        "converted_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    tmp_sidecar = sidecar.parent / (sidecar.name + ".tmp")
    tmp_sidecar.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")
    tmp_sidecar.rename(sidecar)

    return ConvertedDocument(
        source_path=pdf_path,
        markdown_path=md_path,
        markdown=markdown_text,
        engine=engine,
        engine_version=engine_version,
        page_count=page_count,
        source_sha256=source_sha,
    )
