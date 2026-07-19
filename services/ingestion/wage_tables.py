"""Wage-schedule manifest helpers.

The Docling + TPDS wage-table branch that used to live here (#58–#61) was
retired in #90 — the deterministic EPSCA-form parser (epsca_wage_parser.py)
handles every schedule, with the legacy pymupdf4llm path as fallback.  Only
the manifest predicate survives.
"""

from __future__ import annotations

from typing import Any


def is_wage_schedule_entry(entry: dict[str, Any]) -> bool:
    """True when a manifest entry describes a wage schedule document."""
    document_type = str(entry.get("document_type", "")).strip().lower()
    if document_type == "wage_schedule":
        return True

    title = str(entry.get("title", "")).lower()
    source_filename = str(entry.get("source_filename", "")).lower()
    return "wage schedule" in title or "wage schedule" in source_filename
