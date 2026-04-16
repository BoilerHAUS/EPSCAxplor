"""
Stage 3: Classify — assign document metadata from corpus_manifest.

Matches each ExtractedDocument to its corpus_manifest entry by source filename
and returns a ClassifiedDocument carrying the manifest metadata alongside the
extracted content.  The metadata is used by all downstream stages (chunk, embed,
store) to populate the Qdrant payload and the PostgreSQL documents table.
"""

from __future__ import annotations

import datetime
import functools
from dataclasses import dataclass
from pathlib import Path

import yaml

from extract import ExtractedDocument

_HERE = Path(__file__).parent
CORPUS_MANIFEST = _HERE / "corpus_manifest.yaml"


@dataclass(frozen=True)
class DocumentMetadata:
    """Manifest-derived metadata for a single corpus document."""

    union_name: str
    document_type: str
    agreement_scope: str | None
    effective_date: str
    expiry_date: str | None


@dataclass
class ClassifiedDocument:
    """An ExtractedDocument paired with its corpus_manifest metadata."""

    extracted: ExtractedDocument
    metadata: DocumentMetadata


def _to_date_str(value: object) -> str:
    """
    Normalise a value from yaml.safe_load to an ISO-8601 date string.

    PyYAML's safe_load parses bare YAML dates (e.g. ``2025-05-01``) as
    ``datetime.date`` objects.  Quoted strings pass through unchanged.
    This function normalises both representations to a consistent ``str``
    at the system boundary, so downstream stages receive a typed string
    regardless of YAML quoting style.
    """
    if isinstance(value, datetime.date):
        return value.isoformat()
    return str(value)


@functools.lru_cache(maxsize=8)
def _load_manifest_entries(manifest_path: Path) -> list[dict[str, object]]:
    """
    Load and cache manifest entries from a corpus_manifest.yaml file.

    Caching avoids repeated file I/O and YAML parsing when ``classify`` is
    called once per document in a pipeline run against a fixed manifest.
    The cache is keyed on the absolute path, so tests using isolated
    ``tmp_path`` manifests each get their own cache entry.
    """
    with manifest_path.open() as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("documents", []))


def classify(
    doc: ExtractedDocument,
    manifest_path: Path = CORPUS_MANIFEST,
) -> ClassifiedDocument:
    """
    Match an extracted document to its corpus_manifest entry by filename.

    Args:
        doc:           ExtractedDocument produced by extract.py.
        manifest_path: Path to corpus_manifest.yaml (defaults to the file
                       adjacent to this module).

    Returns:
        ClassifiedDocument with metadata drawn from the matching manifest entry.

    Raises:
        ValueError: If no manifest entry's source_filename matches
                    doc.source_path.name.
    """
    entries = _load_manifest_entries(manifest_path)
    filename = doc.source_path.name

    for entry in entries:
        if entry.get("source_filename") == filename:
            expiry_raw = entry.get("expiry_date")
            return ClassifiedDocument(
                extracted=doc,
                metadata=DocumentMetadata(
                    union_name=str(entry["union_name"]),
                    document_type=str(entry["document_type"]),
                    agreement_scope=(
                        str(entry["agreement_scope"])
                        if entry.get("agreement_scope") is not None
                        else None
                    ),
                    effective_date=_to_date_str(entry["effective_date"]),
                    expiry_date=_to_date_str(expiry_raw) if expiry_raw is not None else None,
                ),
            )

    raise ValueError(
        f"No manifest entry found for '{filename}'. "
        f"Add it to {manifest_path.name} before running classify."
    )
