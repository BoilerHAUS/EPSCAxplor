"""Tests for services/api/src/rag/context.py.

Covers:
- _format_date: ISO date → human-readable string
- _resolve_title: title_map lookup with source_filename fallback
- assemble_context: full output formatting for various chunk configurations
"""

from __future__ import annotations

import pytest

from src.rag.context import (
    _DOC_TYPE_LABELS,
    _format_date,
    _resolve_title,
    assemble_context,
)
from src.rag.retrieval import ChunkResult


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_chunk(
    *,
    document_id: str = "doc-001",
    source_filename: str = "IBEW Generation- 2025-2030 Collective Agreement.pdf",
    union_name: str = "IBEW",
    document_type: str = "primary_ca",
    agreement_scope: str | None = "generation",
    effective_date: str | None = "2025-05-01",
    expiry_date: str | None = "2030-04-30",
    article_number: str | None = "Article 12",
    article_title: str | None = "Overtime",
    section_number: str | None = "12.03",
    page_number: int | None = 34,
    is_table: bool = False,
    text: str = "Overtime shall be paid at time and one-half.",
    point_id: str = "pt-1",
    score: float = 0.9,
) -> ChunkResult:
    return ChunkResult(
        point_id=point_id,
        score=score,
        document_id=document_id,
        source_filename=source_filename,
        union_name=union_name,
        document_type=document_type,
        agreement_scope=agreement_scope,
        effective_date=effective_date,
        expiry_date=expiry_date,
        article_number=article_number,
        article_title=article_title,
        section_number=section_number,
        page_number=page_number,
        is_table=is_table,
        text=text,
    )


# ─── _format_date ─────────────────────────────────────────────────────────────


class TestFormatDate:
    def test_none_returns_empty_string(self) -> None:
        assert _format_date(None) == ""

    def test_empty_string_returns_empty_string(self) -> None:
        assert _format_date("") == ""

    def test_first_day_of_month(self) -> None:
        assert _format_date("2025-05-01") == "May 1, 2025"

    def test_last_day_of_month(self) -> None:
        assert _format_date("2030-04-30") == "April 30, 2030"

    def test_no_leading_zero_on_day(self) -> None:
        # Day 1 should render as "1" not "01"
        result = _format_date("2025-01-01")
        assert "01" not in result
        assert "January 1, 2025" == result

    def test_double_digit_day(self) -> None:
        assert _format_date("2025-12-31") == "December 31, 2025"

    def test_unparseable_input_returned_as_is(self) -> None:
        assert _format_date("not-a-date") == "not-a-date"

    def test_partial_date_returned_as_is(self) -> None:
        # "2025-05" is not a valid date.fromisoformat value in Python 3.10
        result = _format_date("2025-05")
        assert result == "2025-05"


# ─── _resolve_title ───────────────────────────────────────────────────────────


class TestResolveTitle:
    def test_returns_title_from_map_when_present(self) -> None:
        chunk = make_chunk(document_id="doc-001")
        title_map = {"doc-001": "IBEW Generation 2025-2030 Collective Agreement"}
        assert _resolve_title(chunk, title_map) == "IBEW Generation 2025-2030 Collective Agreement"

    def test_falls_back_to_source_filename_when_id_absent(self) -> None:
        chunk = make_chunk(
            document_id="doc-999",
            source_filename="fallback.pdf",
        )
        title_map = {"doc-001": "Some Other Document"}
        assert _resolve_title(chunk, title_map) == "fallback.pdf"

    def test_falls_back_to_source_filename_when_map_empty(self) -> None:
        chunk = make_chunk(source_filename="fallback.pdf")
        assert _resolve_title(chunk, {}) == "fallback.pdf"

    def test_empty_string_in_map_falls_back_to_source_filename(self) -> None:
        # An empty string title is falsy — should fall through to source_filename.
        chunk = make_chunk(document_id="doc-001", source_filename="fallback.pdf")
        title_map = {"doc-001": ""}
        assert _resolve_title(chunk, title_map) == "fallback.pdf"


# ─── _DOC_TYPE_LABELS ─────────────────────────────────────────────────────────


class TestDocTypeLabels:
    def test_all_four_types_defined(self) -> None:
        assert _DOC_TYPE_LABELS["primary_ca"] == "Primary Collective Agreement"
        assert _DOC_TYPE_LABELS["nuclear_pa"] == "Nuclear Project Agreement"
        assert _DOC_TYPE_LABELS["moa_supplement"] == "MOA / Supplementary Agreement"
        assert _DOC_TYPE_LABELS["wage_schedule"] == "Wage Schedule"


# ─── assemble_context ─────────────────────────────────────────────────────────


class TestAssembleContext:
    # --- Basic structure ---

    def test_empty_chunks_returns_empty_string(self) -> None:
        assert assemble_context([]) == ""

    def test_single_chunk_contains_source_header(self) -> None:
        result = assemble_context([make_chunk()])
        assert "[SOURCE 1]" in result

    def test_two_chunks_have_sequential_source_numbers(self) -> None:
        result = assemble_context([make_chunk(point_id="a"), make_chunk(point_id="b")])
        assert "[SOURCE 1]" in result
        assert "[SOURCE 2]" in result

    def test_multiple_chunks_separated_by_divider(self) -> None:
        result = assemble_context([make_chunk(point_id="a"), make_chunk(point_id="b")])
        assert "\n\n---\n\n" in result

    def test_single_chunk_no_divider(self) -> None:
        result = assemble_context([make_chunk()])
        assert "---" not in result

    # --- Union and document fields ---

    def test_union_name_present(self) -> None:
        result = assemble_context([make_chunk(union_name="Sheet Metal Workers")])
        assert "Union: Sheet Metal Workers" in result

    def test_document_title_from_title_map(self) -> None:
        chunk = make_chunk(document_id="doc-001")
        title_map = {"doc-001": "IBEW Generation 2025-2030 Collective Agreement"}
        result = assemble_context([chunk], title_map=title_map)
        assert "Document: IBEW Generation 2025-2030 Collective Agreement" in result

    def test_document_title_falls_back_to_source_filename(self) -> None:
        chunk = make_chunk(source_filename="Sheet Metal CA.pdf")
        result = assemble_context([chunk])
        assert "Document: Sheet Metal CA.pdf" in result

    def test_document_type_label_primary_ca(self) -> None:
        result = assemble_context([make_chunk(document_type="primary_ca")])
        assert "Document Type: Primary Collective Agreement" in result

    def test_document_type_label_nuclear_pa(self) -> None:
        result = assemble_context([make_chunk(document_type="nuclear_pa")])
        assert "Document Type: Nuclear Project Agreement" in result

    def test_document_type_label_wage_schedule(self) -> None:
        result = assemble_context([make_chunk(document_type="wage_schedule")])
        assert "Document Type: Wage Schedule" in result

    def test_unknown_document_type_code_used_verbatim(self) -> None:
        result = assemble_context([make_chunk(document_type="other_type")])
        assert "Document Type: other_type" in result

    # --- Date line ---

    def test_effective_and_expiry_dates_rendered(self) -> None:
        chunk = make_chunk(effective_date="2025-05-01", expiry_date="2030-04-30")
        result = assemble_context([chunk])
        assert "Effective: May 1, 2025" in result
        assert "Expires: April 30, 2030" in result
        assert "Effective: May 1, 2025 | Expires: April 30, 2030" in result

    def test_only_effective_date_omits_expires_pipe(self) -> None:
        chunk = make_chunk(effective_date="2025-05-01", expiry_date=None)
        result = assemble_context([chunk])
        assert "Effective: May 1, 2025" in result
        assert "Expires:" not in result

    def test_no_dates_omits_date_line(self) -> None:
        chunk = make_chunk(effective_date=None, expiry_date=None)
        result = assemble_context([chunk])
        assert "Effective:" not in result
        assert "Expires:" not in result

    # --- Article / section line ---

    def test_article_number_and_title_rendered(self) -> None:
        chunk = make_chunk(article_number="Article 12", article_title="Overtime")
        result = assemble_context([chunk])
        assert "Article 12 — Overtime" in result

    def test_article_number_without_title(self) -> None:
        chunk = make_chunk(article_number="Article 5", article_title=None)
        result = assemble_context([chunk])
        assert "Article 5" in result
        assert "—" not in result

    def test_section_number_rendered_with_prefix(self) -> None:
        chunk = make_chunk(section_number="12.03")
        result = assemble_context([chunk])
        assert "Section 12.03" in result

    def test_article_and_section_separated_by_pipe(self) -> None:
        chunk = make_chunk(article_number="Article 12", article_title="Overtime", section_number="12.03")
        result = assemble_context([chunk])
        assert "Article 12 — Overtime | Section 12.03" in result

    def test_no_article_no_section_omits_article_line(self) -> None:
        chunk = make_chunk(article_number=None, article_title=None, section_number=None)
        result = assemble_context([chunk])
        assert "Article" not in result
        assert "Section" not in result

    def test_section_only_without_article(self) -> None:
        chunk = make_chunk(article_number=None, article_title=None, section_number="3.01")
        result = assemble_context([chunk])
        assert "Section 3.01" in result

    # --- Page number ---

    def test_page_number_rendered(self) -> None:
        result = assemble_context([make_chunk(page_number=34)])
        assert "Page: 34" in result

    def test_page_number_zero_rendered(self) -> None:
        result = assemble_context([make_chunk(page_number=0)])
        assert "Page: 0" in result

    def test_none_page_number_omitted(self) -> None:
        result = assemble_context([make_chunk(page_number=None)])
        assert "Page:" not in result

    # --- Chunk text ---

    def test_chunk_text_wrapped_in_quotes(self) -> None:
        result = assemble_context([make_chunk(text="Overtime shall be paid.")])
        assert '"Overtime shall be paid."' in result

    def test_no_title_map_kwarg_uses_source_filename(self) -> None:
        chunk = make_chunk(source_filename="myfile.pdf")
        result = assemble_context([chunk])
        assert "Document: myfile.pdf" in result

    def test_empty_title_map_kwarg_uses_source_filename(self) -> None:
        chunk = make_chunk(source_filename="myfile.pdf")
        result = assemble_context([chunk], title_map={})
        assert "Document: myfile.pdf" in result

    # --- Full spec example ---

    def test_full_spec_output_matches_planning_format(self) -> None:
        """Verify the complete output matches the spec in docs/planning.md §7 Step 3."""
        chunk = make_chunk(
            union_name="IBEW",
            document_id="doc-001",
            document_type="primary_ca",
            effective_date="2025-05-01",
            expiry_date="2030-04-30",
            article_number="Article 12",
            article_title="Overtime",
            section_number="12.03",
            page_number=34,
            text="Overtime shall be paid at time and one-half.",
        )
        title_map = {"doc-001": "IBEW Generation 2025-2030 Collective Agreement"}
        result = assemble_context([chunk], title_map=title_map)

        assert "[SOURCE 1]" in result
        assert "Union: IBEW" in result
        assert "Document: IBEW Generation 2025-2030 Collective Agreement" in result
        assert "Document Type: Primary Collective Agreement" in result
        assert "Effective: May 1, 2025 | Expires: April 30, 2030" in result
        assert "Article 12 — Overtime | Section 12.03" in result
        assert "Page: 34" in result
        assert '"Overtime shall be paid at time and one-half."' in result
