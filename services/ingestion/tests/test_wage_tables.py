"""Tests for wage_tables.is_wage_schedule_entry (the surviving helper after
the Docling + TPDS branch retirement, #90)."""

from __future__ import annotations

from wage_tables import is_wage_schedule_entry


def test_document_type_wage_schedule_matches() -> None:
    assert is_wage_schedule_entry({"document_type": "wage_schedule"}) is True


def test_document_type_is_case_and_whitespace_insensitive() -> None:
    assert is_wage_schedule_entry({"document_type": "  Wage_Schedule "}) is True


def test_title_containing_wage_schedule_matches() -> None:
    entry = {"document_type": "other", "title": "IBEW Wage Schedule 2025"}
    assert is_wage_schedule_entry(entry) is True


def test_source_filename_containing_wage_schedule_matches() -> None:
    entry = {"source_filename": "ua wage schedule may 2025.pdf"}
    assert is_wage_schedule_entry(entry) is True


def test_primary_ca_entry_does_not_match() -> None:
    entry = {
        "document_type": "primary_ca",
        "title": "IBEW Generation 2025-2030 Collective Agreement",
        "source_filename": "IBEW Generation- 2025-2030 Collective Agreement.pdf",
    }
    assert is_wage_schedule_entry(entry) is False


def test_empty_entry_does_not_match() -> None:
    assert is_wage_schedule_entry({}) is False


def test_general_dues_entry_does_not_match() -> None:
    # The Teamsters dues form is filed beside a wage schedule on epsca.org but
    # carries no rate table, so it must stay on the legacy extraction path —
    # the EPSCA wage-form parser would find no classification rows in it (#179).
    entry = {
        "document_type": "general",
        "title": "Teamsters Union Dues - May 2025",
        "source_filename": "Union Dues - May 2025.pdf",
    }
    assert is_wage_schedule_entry(entry) is False
