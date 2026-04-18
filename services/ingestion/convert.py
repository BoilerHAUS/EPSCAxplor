"""
Stage 1b: Convert — PDF to Markdown pre-processing.

Converts each PDF to structured Markdown before chunking, preserving table
structure (pipe-delimited rows) that pdfplumber's naive text extraction destroys.
Critical for wage schedule PDFs which are primarily tables.

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
from dataclasses import dataclass
from pathlib import Path

_SUPPORTED_ENGINES = frozenset({"pymupdf4llm"})
_PAGE_NUM_RE = re.compile(r"<!--\s*page:\s*(\d+)\s*-->")


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
        engine:       Conversion backend. Currently only "pymupdf4llm" is supported.
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
