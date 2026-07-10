"""Tests for the deterministic EPSCA wage schedule parser.

Fixtures are real page text extracted (pdfplumber layout mode) from the
Phase 1 corpus wage schedule PDFs — one page per union layout variant:

- epsca_wage_ibew_lu105_page1.txt  IBEW E-6-C LU 105 Hamilton (9 rate columns)
- epsca_wage_ibew_lu105_page2.txt  IBEW E-6-C notes page (overtime / union funds)
- epsca_wage_sm_lu235_page1.txt    Sheet Metal SM-1 LU 235 Windsor (8 rate columns)
- epsca_wage_ua_lu46_page1.txt     UA UA-7 LU 46 Toronto (7 rate columns)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epsca_wage_parser import (
    build_wage_chunks,
    parse_wage_schedule_text,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ibew_page():
    page = parse_wage_schedule_text(_load("epsca_wage_ibew_lu105_page1.txt"), pdf_page_number=1)
    assert page is not None
    return page


@pytest.fixture(scope="module")
def ibew_notes_page():
    page = parse_wage_schedule_text(_load("epsca_wage_ibew_lu105_page2.txt"), pdf_page_number=2)
    assert page is not None
    return page


@pytest.fixture(scope="module")
def sm_page():
    page = parse_wage_schedule_text(_load("epsca_wage_sm_lu235_page1.txt"), pdf_page_number=1)
    assert page is not None
    return page


@pytest.fixture(scope="module")
def ua_page():
    page = parse_wage_schedule_text(_load("epsca_wage_ua_lu46_page1.txt"), pdf_page_number=1)
    assert page is not None
    return page


# ─── Header parsing ───────────────────────────────────────────────────────────


def test_ibew_header(ibew_page):
    assert ibew_page.map_code == "E-6-C"
    assert ibew_page.local == "Local 105"
    assert ibew_page.city == "Hamilton"
    assert ibew_page.trade == "ELECTRICAL WORKERS"
    assert ibew_page.revised == "May 1, 2025"
    assert ibew_page.page_in_schedule == 1
    assert ibew_page.pages_in_schedule == 2


def test_sm_header(sm_page):
    assert sm_page.map_code == "SM-1"
    assert sm_page.local == "Local 235"
    assert sm_page.city == "Windsor"
    assert sm_page.trade == "SHEET METAL WORKERS"


def test_ua_header(ua_page):
    assert ua_page.map_code == "UA-7"
    assert ua_page.local == "Local 46"
    assert ua_page.city == "Toronto"
    assert ua_page.trade == "PLUMBERS"


def test_non_wage_page_returns_none():
    assert parse_wage_schedule_text("ARTICLE 12 — OVERTIME\n12.01 Blah.", 1) is None


# ─── Classification groups ────────────────────────────────────────────────────


def _group_by_name(page, needle: str):
    for group in page.groups:
        if any(needle in name for name in group.names):
            return group
    raise AssertionError(f"No group named like {needle!r} in {[g.names for g in page.groups]}")


def test_ibew_journeyman_group(ibew_page):
    group = _group_by_name(ibew_page, "JOURNEYMAN")
    assert "410135" in group.occupation_codes
    assert "410136" in group.occupation_codes
    assert "410137" in group.occupation_codes
    assert "07-6" in group.grade_steps
    row_2025 = next(r for r in group.rows if r.effective_date == "2025-05-01")
    assert row_2025.values[0] == pytest.approx(46.65)   # base hourly rate
    assert row_2025.values[5] == pytest.approx(73.72)   # total wage package
    assert len(row_2025.values) == 9
    assert row_2025.sum_valid
    assert row_2025.columns[0] == "base hourly rate"
    assert row_2025.columns[5] == "total wage package"


def test_ibew_foreman_group_includes_electrician_label(ibew_page):
    group = _group_by_name(ibew_page, "FOREMAN")
    assert any("ELECTRICIAN" == n for n in group.names)
    assert "410165" in group.occupation_codes
    row_2025 = next(r for r in group.rows if r.effective_date == "2025-05-01")
    assert row_2025.values[0] == pytest.approx(52.25)


def test_ibew_apprentice_periods_carry_parent_label(ibew_page):
    first_period = _group_by_name(ibew_page, "1st Period")
    assert any("APPRENTICE" in n for n in first_period.names)
    second_period = _group_by_name(ibew_page, "2nd Period")
    assert any("APPRENTICE" in n for n in second_period.names)
    row = next(r for r in second_period.rows if r.effective_date == "2025-05-01")
    assert row.values[0] == pytest.approx(23.33)


def test_sm_journeyman_group(sm_page):
    group = _group_by_name(sm_page, "JOURNEYMAN")
    row_2025 = next(r for r in group.rows if r.effective_date == "2025-05-01")
    assert row_2025.values[0] == pytest.approx(48.16)
    assert len(row_2025.values) == 8
    assert row_2025.sum_valid
    assert row_2025.columns[3] == "pension"


def test_sm_annotated_classification(sm_page):
    group = _group_by_name(sm_page, "PROBATIONARY EMPLOYEE")
    assert "445525" in group.occupation_codes
    assert any("50% of Journeyman" in (a or "") for a in group.annotations)


def test_ua_journeyman_group(ua_page):
    group = _group_by_name(ua_page, "JOURNEYMAN")
    assert "450035" in group.occupation_codes
    assert "450036" in group.occupation_codes  # PIPEWELDER
    row_2025 = next(r for r in group.rows if r.effective_date == "2025-05-01")
    assert row_2025.values[0] == pytest.approx(52.65)
    assert len(row_2025.values) == 7
    assert row_2025.sum_valid


def test_ua_foreman_annotation(ua_page):
    group = _group_by_name(ua_page, "FOREMAN")
    assert any("15% above" in (a or "") for a in group.annotations)


def test_every_group_has_rows(ibew_page, sm_page, ua_page):
    for page in (ibew_page, sm_page, ua_page):
        assert page.groups
        for group in page.groups:
            assert group.rows, f"group {group.names} has no rate rows"
            for row in group.rows:
                assert row.sum_valid, f"sum check failed for {group.names} {row.effective_date}"


# ─── Layout variants (plain-text extraction, header-driven columns) ──────────


def test_ibew_lu773_plain_text_variant():
    """E-1-C LU 773 Windsor: oversized page geometry (plain text layer only),
    8 columns with an education-fund tail instead of Bill 162."""
    page = parse_wage_schedule_text(
        _load("epsca_wage_ibew_lu773_page1_plain.txt"), pdf_page_number=3
    )
    assert page is not None
    assert page.map_code == "E-1-C"
    assert page.local == "Local 773"
    assert page.city == "Windsor"
    group = _group_by_name(page, "FOREMAN")
    row_2025 = next(r for r in group.rows if r.effective_date == "2025-05-01")
    assert row_2025.values[0] == pytest.approx(55.87)
    assert len(row_2025.values) == 8
    assert row_2025.columns[3] == "pension"
    assert row_2025.columns[5] == "total wage package"
    assert row_2025.columns[6] == "education union fund"
    assert row_2025.sum_valid


def test_ibew_lu353_north_rrsp_variant():
    """E-14-C LU 353 North: RRSP column appears from 2025 onward, so column
    count differs between rows of the same table."""
    page = parse_wage_schedule_text(
        _load("epsca_wage_ibew_lu353N_page1_plain.txt"), pdf_page_number=21
    )
    assert page is not None
    group = _group_by_name(page, "JOURNEYMAN")
    row_2024 = next(r for r in group.rows if r.effective_date == "2024-05-01")
    row_2025 = next(r for r in group.rows if r.effective_date == "2025-05-01")
    assert len(row_2024.values) == 8
    assert row_2024.columns[5] == "total wage package"
    assert len(row_2025.values) == 9
    assert row_2025.columns[4] == "RRSP"
    assert row_2025.columns[6] == "total wage package"
    assert row_2024.sum_valid and row_2025.sum_valid


# ─── Notes pages ──────────────────────────────────────────────────────────────


def test_ibew_notes_page(ibew_notes_page):
    assert ibew_notes_page.page_in_schedule == 2
    assert not ibew_notes_page.groups
    assert ibew_notes_page.notes is not None
    assert "Overtime Rate" in ibew_notes_page.notes
    assert "UNION FUNDS" in ibew_notes_page.notes


def test_rates_page_footnotes_kept(ua_page):
    # Trailing footnotes on rates pages are preserved as notes.
    assert ua_page.notes is not None
    assert "over 71" in ua_page.notes


# ─── Chunk building ───────────────────────────────────────────────────────────


def test_build_chunks_journeyman_text(ibew_page, ibew_notes_page):
    chunks = build_wage_chunks([ibew_page, ibew_notes_page], union_name="IBEW")

    journeyman = [
        c for c in chunks if "JOURNEYMAN" in c.text and c.is_table
    ]
    assert len(journeyman) == 1
    text = journeyman[0].text
    # Identity — the chunk must stand alone.
    assert "IBEW" in text
    assert "Local 105" in text
    assert "Hamilton" in text
    assert "E-6-C" in text
    # The May 1, 2025 journeyperson base rate — the query that started it all.
    assert "2025-05-01" in text
    assert "$46.65" in text
    assert "base hourly rate" in text
    assert "total wage package $73.72" in text
    # Should fit the embedding-friendly chunk budget (~500 tokens ≈ 2000 chars).
    assert len(text) <= 2600


def test_build_chunks_metadata_and_indexing(ibew_page, ibew_notes_page):
    chunks = build_wage_chunks([ibew_page, ibew_notes_page], union_name="IBEW")

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    rate_chunks = [c for c in chunks if c.is_table]
    assert rate_chunks
    for c in rate_chunks:
        assert c.metadata is not None
        assert c.metadata["wage_schedule"] is True
        assert c.metadata["table_pipeline"] == "epsca_form"
        assert c.metadata["local"] == "Local 105"
        assert c.metadata["city"] == "Hamilton"
        rates = c.metadata["rates"]
        assert isinstance(rates, list) and rates
        assert "effective_date" in rates[0]
        assert "base hourly rate" in rates[0]


def test_build_chunks_notes(ibew_page, ibew_notes_page):
    chunks = build_wage_chunks([ibew_page, ibew_notes_page], union_name="IBEW")
    notes = [c for c in chunks if not c.is_table]
    assert notes
    joined = "\n".join(c.text for c in notes)
    assert "Overtime Rate" in joined
    for c in notes:
        assert "Local 105" in c.text  # every notes chunk carries its local identity
        assert len(c.text) <= 2600
