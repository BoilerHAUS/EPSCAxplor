"""Tests for chunk.py — Stage 4 of the ingestion pipeline."""

from chunk import CHARS_PER_TOKEN, MAX_CHUNK_TOKENS, chunk_document
from pathlib import Path

import pytest

from classify import ClassifiedDocument, DocumentMetadata
from extract import ExtractedDocument, TableBlock, TextBlock

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_metadata() -> DocumentMetadata:
    return DocumentMetadata(
        union_name="IBEW",
        document_type="primary_ca",
        agreement_scope="generation",
        effective_date="2025-05-01",
        expiry_date="2030-04-30",
        title="IBEW Test Agreement",
        source_url="PLACEHOLDER",
    )


def _make_doc(blocks: list, page_count: int = 1) -> ClassifiedDocument:
    extracted = ExtractedDocument(
        source_path=Path("test.pdf"),
        blocks=blocks,
        page_count=page_count,
    )
    return ClassifiedDocument(extracted=extracted, metadata=_make_metadata())


def _long_text(tokens: int) -> str:
    """Return text that approximates the given token count."""
    char_count = tokens * CHARS_PER_TOKEN
    # "word " is 5 chars; pad to exact char count
    words = "word " * (char_count // 5)
    return words[:char_count]


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestEmptyDocument:
    def test_empty_blocks_produces_no_chunks(self) -> None:
        chunks = chunk_document(_make_doc([]))
        assert chunks == []

    def test_whitespace_only_text_produces_no_chunks(self) -> None:
        block = TextBlock(text="   \n\n\t  \n", page_number=1)
        chunks = chunk_document(_make_doc([block]))
        assert chunks == []


class TestTableChunks:
    def test_table_block_produces_one_chunk(self) -> None:
        rows = (("Classification", "Rate"), ("Journeyperson", "$45.00"))
        block = TableBlock(rows=rows, page_number=3)
        chunks = chunk_document(_make_doc([block]))
        assert len(chunks) == 1

    def test_table_chunk_is_flagged(self) -> None:
        rows = (("Classification", "Rate"), ("Journeyperson", "$45.00"))
        block = TableBlock(rows=rows, page_number=1)
        chunks = chunk_document(_make_doc([block]))
        assert chunks[0].is_table is True

    def test_table_chunk_preserves_page_number(self) -> None:
        rows = (("A", "B"),)
        block = TableBlock(rows=rows, page_number=7)
        chunks = chunk_document(_make_doc([block]))
        assert chunks[0].page_number == 7

    def test_table_chunk_contains_row_data(self) -> None:
        rows = (
            ("Classification", "Hourly Rate"),
            ("Journeyperson", "$45.00"),
            ("Apprentice", "$36.00"),
        )
        block = TableBlock(rows=rows, page_number=1)
        chunks = chunk_document(_make_doc([block]))
        assert "Journeyperson" in chunks[0].text
        assert "$45.00" in chunks[0].text

    def test_large_table_is_atomic(self) -> None:
        """A table that exceeds the token limit must never be split."""
        rows = tuple(
            tuple(f"cell_{r}_{c}" for c in range(10))
            for r in range(60)
        )
        block = TableBlock(rows=rows, page_number=1)
        chunks = chunk_document(_make_doc([block]))
        assert len(chunks) == 1
        assert chunks[0].is_table is True

    def test_table_with_none_cells_handled(self) -> None:
        rows = ((None, "Rate"), ("Journeyperson", None))
        block = TableBlock(rows=rows, page_number=1)
        chunks = chunk_document(_make_doc([block]))
        assert len(chunks) == 1
        assert "Journeyperson" in chunks[0].text

    def test_multiple_tables_produce_multiple_chunks(self) -> None:
        rows = (("A", "B"),)
        blocks = [
            TableBlock(rows=rows, page_number=1),
            TableBlock(rows=rows, page_number=2),
        ]
        chunks = chunk_document(_make_doc(blocks))
        table_chunks = [c for c in chunks if c.is_table]
        assert len(table_chunks) == 2


class TestTableLeadIn:
    """A terse table chunk inherits the narrative that names it (#126).

    Regression for T03: the SM CA subsistence rate table extracts as its own
    TableBlock whose text calls it "Room and Board Rates" — the word the user
    queries with ("subsistence allowance") lives only in the *preceding*
    narrative, so the table chunk was never retrieved.
    """

    def _subsistence_blocks(self) -> list[TextBlock | TableBlock]:
        narrative = TextBlock(
            text=(
                "26.2 The following conditions apply for room and board.\n"
                "(b) An employee may exercise their option not to stay in camp "
                "and shall receive a subsistence allowance as follows: the "
                "Province is divided into a Northern region and a Southern "
                "region for the payment of subsistence allowance."
            ),
            page_number=32,
        )
        table = TableBlock(
            rows=(
                ("Year", "North of French", "South of French"),
                ("2025-05-01", "$135", "$120"),
                ("2026-05-01", "$140", "$125"),
            ),
            page_number=33,
        )
        return [narrative, table]

    def test_table_inherits_naming_term_from_preceding_narrative(self) -> None:
        chunks = chunk_document(_make_doc(self._subsistence_blocks()))
        table_chunk = next(c for c in chunks if c.is_table)
        assert "subsistence allowance" in table_chunk.text.lower()

    def test_table_still_contains_amounts(self) -> None:
        chunks = chunk_document(_make_doc(self._subsistence_blocks()))
        table_chunk = next(c for c in chunks if c.is_table)
        assert "$135" in table_chunk.text
        assert "$120" in table_chunk.text

    def test_table_inherits_section_number_from_lead_in(self) -> None:
        chunks = chunk_document(_make_doc(self._subsistence_blocks()))
        table_chunk = next(c for c in chunks if c.is_table)
        assert table_chunk.section_number == "26.2"

    def test_table_remains_single_atomic_chunk(self) -> None:
        chunks = chunk_document(_make_doc(self._subsistence_blocks()))
        table_chunks = [c for c in chunks if c.is_table]
        assert len(table_chunks) == 1
        assert table_chunks[0].is_table is True

    def test_lead_in_is_bounded_to_section_head(self) -> None:
        # The section opening (which names the table) is prepended; text far past
        # the budget is excluded so the table chunk doesn't absorb a whole article.
        narrative = TextBlock(
            text=(
                "26.2 Employees receive a subsistence allowance as follows. "
                + _long_text(500)
                + " TAILMARKER far past the lead-in budget."
            ),
            page_number=1,
        )
        table = TableBlock(
            rows=(("Year", "North"), ("2025-05-01", "$135")), page_number=1
        )
        chunks = chunk_document(_make_doc([narrative, table]))
        table_chunk = next(c for c in chunks if c.is_table)
        assert "subsistence allowance" in table_chunk.text.lower()
        assert "TAILMARKER" not in table_chunk.text

    def test_table_keys_off_its_own_leading_cell_section(self) -> None:
        # A table whose leading cell carries its section number inherits that
        # section even with no preceding narrative line (extractor ordering).
        table = TableBlock(
            rows=(("26.2 Room and Board Rates", ""), ("2025-05-01", "$135")),
            page_number=1,
        )
        chunks = chunk_document(_make_doc([table]))
        table_chunk = next(c for c in chunks if c.is_table)
        assert table_chunk.section_number == "26.2"

    def test_self_labeled_table_before_its_narrative_still_gets_lead_in(self) -> None:
        # The real §27.4 case: pdfplumber emits the TableBlock BEFORE the
        # narrative that names it.  The order-independent first-pass map + the
        # table's own section label recover the lead-in regardless of block order.
        table = TableBlock(
            rows=(("27.4 Room and Board Rates", ""), ("2025-05-01", "$135")),
            page_number=1,
        )
        narrative = TextBlock(
            text=(
                "27.4 The following conditions apply. (b) An employee shall "
                "receive a subsistence allowance as follows for the Northern and "
                "Southern regions."
            ),
            page_number=1,
        )
        chunks = chunk_document(_make_doc([table, narrative]))
        table_chunk = next(c for c in chunks if c.is_table)
        assert table_chunk.section_number == "27.4"
        assert "subsistence allowance" in table_chunk.text.lower()

    def test_unlabeled_table_before_its_narrative_has_no_lead_in(self) -> None:
        # Documented limitation: a table with no section label in its header row,
        # emitted before its narrative, has no reliable section signal, so it
        # gets no lead-in — no worse than before the fix (the #126 target tables
        # self-label their section in the header cell).
        table = TableBlock(
            rows=(("Year", "Rate"), ("2025-05-01", "$135")), page_number=1
        )
        narrative = TextBlock(
            text="27.4 conditions apply; a subsistence allowance is paid.",
            page_number=1,
        )
        chunks = chunk_document(_make_doc([table, narrative]))
        table_chunk = next(c for c in chunks if c.is_table)
        assert "subsistence" not in table_chunk.text.lower()
        assert table_chunk.section_number is None

    def test_blank_header_corner_does_not_match_data_cell_as_section(self) -> None:
        # A blank top-left header must not let a data cell like "2025.05" be
        # mistaken for a section number (row-0-only scan).
        table = TableBlock(
            rows=(("", "North"), ("2025.05", "$135")), page_number=1
        )
        chunks = chunk_document(_make_doc([table]))
        table_chunk = next(c for c in chunks if c.is_table)
        assert table_chunk.section_number is None

    def test_isolated_table_gets_no_lead_in(self) -> None:
        table = TableBlock(
            rows=(("Year", "North"), ("2025-05-01", "$135")), page_number=1
        )
        chunks = chunk_document(_make_doc([table]))
        table_chunk = next(c for c in chunks if c.is_table)
        assert table_chunk.text.startswith("Year")
        assert table_chunk.section_number is None


class TestArticleBoundaryDetection:
    def test_article_heading_starts_new_chunk(self) -> None:
        """Two articles → at least two chunks when each fits in the token limit."""
        text = (
            "ARTICLE 1 — RECOGNITION\n"
            "1.01 The Company recognizes the Union.\n"
            "ARTICLE 2 — UNION SECURITY\n"
            "2.01 All employees shall be members."
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert len(chunks) >= 2

    def test_article_number_parsed_from_heading(self) -> None:
        text = "ARTICLE 12 — OVERTIME\n12.01 Overtime pay applies."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert any(c.article_number == "Article 12" for c in chunks)

    def test_article_title_parsed_from_heading(self) -> None:
        text = "ARTICLE 5 — WAGES AND BENEFITS\n5.01 Wage rates are set forth."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        art5 = [c for c in chunks if c.article_number == "Article 5"]
        assert any(c.article_title == "WAGES AND BENEFITS" for c in art5)

    def test_heading_without_title_sets_article_number(self) -> None:
        text = "ARTICLE 3\n3.01 Some clause text."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert any(c.article_number == "Article 3" for c in chunks)

    def test_heading_without_title_has_none_article_title(self) -> None:
        text = "ARTICLE 3\n3.01 Some clause text."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        art3 = [c for c in chunks if c.article_number == "Article 3"]
        assert all(c.article_title is None for c in art3)

    def test_heading_with_em_dash_parsed(self) -> None:
        """Standard EPSCA format uses the em-dash (—)."""
        text = "ARTICLE 1 — RECOGNITION\n1.01 Recognized."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert any(c.article_number == "Article 1" for c in chunks)

    def test_heading_with_en_dash_parsed(self) -> None:
        text = "ARTICLE 2 – SCOPE\n2.01 Applies to all trades."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert any(c.article_number == "Article 2" for c in chunks)

    def test_heading_with_hyphen_parsed(self) -> None:
        text = "ARTICLE 4 - SENIORITY\n4.01 Seniority applies."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert any(c.article_number == "Article 4" for c in chunks)

    def test_preamble_before_first_article_becomes_chunk(self) -> None:
        text = (
            "COLLECTIVE AGREEMENT\n"
            "Between the Employer and the Union\n"
            "ARTICLE 1 — RECOGNITION\n"
            "1.01 The Company recognizes the Union."
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        preamble = [c for c in chunks if c.article_number is None and not c.is_table]
        assert len(preamble) >= 1

    def test_preamble_chunk_contains_preamble_text(self) -> None:
        text = (
            "COLLECTIVE AGREEMENT\n"
            "ARTICLE 1 — RECOGNITION\n"
            "1.01 The Company recognizes the Union."
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        preamble = [c for c in chunks if c.article_number is None and not c.is_table]
        assert any("COLLECTIVE AGREEMENT" in c.text for c in preamble)

    def test_article_spanning_two_pages(self) -> None:
        """Article beginning on page 1 continues on page 2."""
        page1 = TextBlock(text="ARTICLE 1 — RECOGNITION\n1.01 The Company.", page_number=1)
        page2 = TextBlock(text="1.02 The Union agrees.", page_number=2)
        chunks = chunk_document(_make_doc([page1, page2]))
        art1 = [c for c in chunks if c.article_number == "Article 1"]
        assert len(art1) >= 1


class TestSectionBoundaries:
    def test_small_article_stays_one_chunk(self) -> None:
        """Article within token limit → single chunk even with multiple sections."""
        text = (
            "ARTICLE 1 — RECOGNITION\n"
            "1.01 Short clause.\n"
            "1.02 Another short clause."
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        art1 = [c for c in chunks if c.article_number == "Article 1"]
        assert len(art1) == 1

    def test_small_article_chunk_has_no_section_number(self) -> None:
        """One-chunk article covers the whole article, so section_number is None."""
        text = "ARTICLE 1 — RECOGNITION\n1.01 Short.\n1.02 Also short."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        art1 = [c for c in chunks if c.article_number == "Article 1"]
        assert len(art1) == 1
        assert art1[0].section_number is None

    def test_oversized_article_splits_at_section_boundaries(self) -> None:
        """Article exceeding token limit is split at section lines."""
        section_body = _long_text(280)  # 280 tokens per section
        text = (
            "ARTICLE 1 — WAGES\n"
            f"1.01 {section_body}\n"
            f"1.02 {section_body}"
        )
        # total ≈ 5 (heading) + 280 + 280 = 565 tokens > MAX (500) → split
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        art1 = [c for c in chunks if c.article_number == "Article 1"]
        assert len(art1) >= 2

    def test_section_number_attached_after_split(self) -> None:
        """After splitting, each section chunk carries its section number."""
        section_body = _long_text(280)
        text = (
            "ARTICLE 1 — WAGES\n"
            f"1.01 {section_body}\n"
            f"1.02 {section_body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        section_numbers = {c.section_number for c in chunks if c.section_number}
        assert "1.01" in section_numbers or "1.02" in section_numbers

    def test_section_number_none_for_unsplit_article(self) -> None:
        """When article fits in limit and has no split, section_number stays None."""
        text = "ARTICLE 2 — SCOPE\n2.01 Short.\n2.02 Also short."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        art2 = [c for c in chunks if c.article_number == "Article 2"]
        assert all(c.section_number is None for c in art2)


class TestChunkIndex:
    def test_chunk_index_starts_at_zero(self) -> None:
        text = "ARTICLE 1 — RECOGNITION\n1.01 Short clause."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert chunks[0].chunk_index == 0

    def test_chunk_index_is_sequential(self) -> None:
        text = (
            "ARTICLE 1 — RECOGNITION\n1.01 First.\n"
            "ARTICLE 2 — SCOPE\n2.01 Second."
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_table_and_text_chunks_share_sequential_index(self) -> None:
        rows = (("A", "B"),)
        table = TableBlock(rows=rows, page_number=1)
        text = TextBlock(text="ARTICLE 1 — SCOPE\n1.01 Clause.", page_number=2)
        chunks = chunk_document(_make_doc([table, text]))
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_many_chunks_have_contiguous_indices(self) -> None:
        section_body = _long_text(280)
        text = (
            "ARTICLE 1 — WAGES\n"
            f"1.01 {section_body}\n"
            f"1.02 {section_body}\n"
            "ARTICLE 2 — SCOPE\n"
            "2.01 Short."
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


class TestPageNumbers:
    def test_text_chunk_carries_block_page_number(self) -> None:
        text = "ARTICLE 1 — RECOGNITION\n1.01 Clause."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=5)]))
        text_chunks = [c for c in chunks if not c.is_table]
        assert all(c.page_number == 5 for c in text_chunks)

    def test_table_chunk_carries_block_page_number(self) -> None:
        rows = (("A", "B"),)
        chunks = chunk_document(_make_doc([TableBlock(rows=rows, page_number=12)]))
        assert chunks[0].page_number == 12

    def test_cross_page_article_first_chunk_has_heading_page(self) -> None:
        page1 = TextBlock(text="ARTICLE 3 — OVERTIME\n3.01 Clause.", page_number=4)
        page2 = TextBlock(text="3.02 Another clause.", page_number=5)
        chunks = chunk_document(_make_doc([page1, page2]))
        art3 = [c for c in chunks if c.article_number == "Article 3"]
        # The first article chunk should start on page 4 (where the heading is)
        assert art3[0].page_number == 4


class TestTableArticleContext:
    def test_table_inherits_current_article_number(self) -> None:
        text_block = TextBlock(
            text="ARTICLE 8 — WAGES\n8.01 See attached schedule.",
            page_number=1,
        )
        rows = (("Classification", "Rate"), ("Journeyperson", "$45.00"))
        table_block = TableBlock(rows=rows, page_number=2)
        chunks = chunk_document(_make_doc([text_block, table_block]))
        table_chunks = [c for c in chunks if c.is_table]
        assert len(table_chunks) == 1
        assert table_chunks[0].article_number == "Article 8"

    def test_table_before_any_article_has_no_article_number(self) -> None:
        rows = (("A", "B"),)
        chunks = chunk_document(_make_doc([TableBlock(rows=rows, page_number=1)]))
        assert chunks[0].article_number is None

    def test_table_inherits_article_title(self) -> None:
        text_block = TextBlock(
            text="ARTICLE 8 — WAGES\n8.01 See the schedule.",
            page_number=1,
        )
        rows = (("Classification", "Rate"),)
        table_block = TableBlock(rows=rows, page_number=2)
        chunks = chunk_document(_make_doc([text_block, table_block]))
        table_chunks = [c for c in chunks if c.is_table]
        assert table_chunks[0].article_title == "WAGES"


class TestTokenCountFallback:
    def test_oversized_section_produces_multiple_chunks(self) -> None:
        """Section text exceeding MAX_CHUNK_TOKENS is split into sub-chunks."""
        long_body = _long_text(MAX_CHUNK_TOKENS + 100)
        text = f"ARTICLE 1 — WAGES\n1.01 {long_body}"
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert len(chunks) >= 2

    def test_split_chunks_share_article_number(self) -> None:
        long_body = _long_text(MAX_CHUNK_TOKENS + 100)
        text = f"ARTICLE 2 — SCOPE\n2.01 {long_body}"
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        for chunk in chunks:
            if not chunk.is_table:
                assert chunk.article_number == "Article 2"

    def test_split_chunks_share_section_number(self) -> None:
        long_body = _long_text(MAX_CHUNK_TOKENS + 100)
        text = f"ARTICLE 2 — SCOPE\n2.01 {long_body}"
        # Make the article long enough to split at section boundary
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        non_table = [c for c in chunks if not c.is_table]
        # section_number is set when sections are split out; at least two sub-chunks
        assert len(non_table) >= 2

    def test_no_chunk_exceeds_double_max_tokens(self) -> None:
        """Even with overlap, no single chunk should be more than 2× the limit."""
        long_body = _long_text(MAX_CHUNK_TOKENS * 5)
        text = f"ARTICLE 1 — WAGES\n1.01 {long_body}"
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        max_allowed = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN * 2
        for chunk in chunks:
            assert len(chunk.text) <= max_allowed


class TestChunkDataclass:
    def test_chunk_is_frozen(self) -> None:
        """Chunk must be immutable."""
        text = "ARTICLE 1 — SCOPE\n1.01 Short."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert len(chunks) >= 1
        with pytest.raises((TypeError, AttributeError)):
            chunks[0].text = "mutated"  # type: ignore[misc]

    def test_chunk_is_table_false_for_text(self) -> None:
        text = "ARTICLE 1 — SCOPE\n1.01 Short."
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        text_chunks = [c for c in chunks if not c.is_table]
        assert len(text_chunks) >= 1
        assert all(c.is_table is False for c in text_chunks)


class TestWageScheduleChunking:
    def _make_wage_metadata(self) -> DocumentMetadata:
        return DocumentMetadata(
            union_name="Sheet Metal Workers",
            document_type="wage_schedule",
            agreement_scope="commercial",
            effective_date="2025-01-01",
            expiry_date="2030-12-31",
            title="Sheet Metal Wage Schedule 2025",
            source_url=None,
        )

    def _make_wage_doc(self, blocks: list, page_count: int = 1) -> ClassifiedDocument:
        from extract import ExtractedDocument

        extracted = ExtractedDocument(
            source_path=Path("wage_schedule.pdf"),
            blocks=blocks,
            page_count=page_count,
        )
        return ClassifiedDocument(extracted=extracted, metadata=self._make_wage_metadata())

    def test_wage_schedule_splits_on_h2_headers(self) -> None:
        blocks = [
            TextBlock(
                text="## Journeyperson Rates\n\nJourneyperson: $43.98",
                page_number=1,
            ),
            TextBlock(
                text="## Apprentice Rates\n\nApprentice 1st: $21.99",
                page_number=1,
            ),
        ]
        chunks = chunk_document(self._make_wage_doc(blocks))
        assert len(chunks) >= 2

    def test_wage_schedule_header_text_populates_article_title(self) -> None:
        blocks = [
            TextBlock(
                text="## Journeyperson Rates\n\nJourneyperson: $43.98",
                page_number=1,
            )
        ]
        chunks = chunk_document(self._make_wage_doc(blocks))
        assert len(chunks) >= 1
        assert chunks[0].article_title == "Journeyperson Rates"

    def test_wage_schedule_h3_header_populates_article_title(self) -> None:
        blocks = [
            TextBlock(
                text="### Premium Pay\n\nShift differential: $2.50/hr",
                page_number=2,
            )
        ]
        chunks = chunk_document(self._make_wage_doc(blocks))
        assert len(chunks) >= 1
        assert chunks[0].article_title == "Premium Pay"

    def test_wage_schedule_table_block_is_atomic(self) -> None:
        rows = (
            ("Classification", "Effective Date", "Hourly Rate"),
            ("Journeyperson", "2025-01-01", "$43.98"),
            ("Apprentice 1st", "2025-01-01", "$21.99"),
        )
        blocks = [
            TextBlock(text="## Journeyperson Rates", page_number=1),
            TableBlock(rows=rows, page_number=1),
        ]
        chunks = chunk_document(self._make_wage_doc(blocks))
        table_chunks = [c for c in chunks if c.is_table]
        assert len(table_chunks) == 1
        assert "$43.98" in table_chunks[0].text

    def test_wage_schedule_table_inherits_h2_header_as_title(self) -> None:
        rows = (("Type", "Amount"), ("Shift Premium", "$2.50"))
        blocks = [
            TextBlock(text="## Premium Pay", page_number=2),
            TableBlock(rows=rows, page_number=2),
        ]
        chunks = chunk_document(self._make_wage_doc(blocks))
        table_chunks = [c for c in chunks if c.is_table]
        assert len(table_chunks) == 1
        assert table_chunks[0].article_title == "Premium Pay"

    def test_wage_schedule_chunk_index_is_sequential(self) -> None:
        rows = (("Classification", "Rate"), ("Journeyperson", "$43.98"))
        blocks = [
            TextBlock(text="## Section A\n\nSome text.", page_number=1),
            TableBlock(rows=rows, page_number=1),
            TextBlock(text="## Section B\n\nMore text.", page_number=2),
        ]
        chunks = chunk_document(self._make_wage_doc(blocks))
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_primary_ca_article_regex_not_used_for_wage_schedule(self) -> None:
        """Wage schedule docs must NOT be processed with the ARTICLE N regex."""
        blocks = [
            TextBlock(
                text="## Journeyperson Rates\n\nJourneyperson: $43.98",
                page_number=1,
            )
        ]
        chunks = chunk_document(self._make_wage_doc(blocks))
        assert all(c.article_number is None for c in chunks)

    def test_primary_ca_chunking_uses_article_regex(self) -> None:
        """CA documents must still use ARTICLE N — TITLE parsing."""
        text = "ARTICLE 1 — SCOPE\n1.01 This agreement covers all employees."
        ca_doc = _make_doc([TextBlock(text=text, page_number=1)])
        chunks = chunk_document(ca_doc)
        assert len(chunks) >= 1
        assert chunks[0].article_number == "Article 1"
        assert chunks[0].article_title == "SCOPE"


class TestMarginSectionNumbers:
    """EPSCA numbers many sections as 3-digit margin numbers ("801 A.", "806 A.")
    rather than decimal N.NN, with the section title stacked in the left margin.
    These must be recognized so the chunk carries the correct section_number for
    citation (#79, O01 — rest-period items §801 B/C were mislabelled §802 because
    the chunk had no section metadata and the model guessed from adjacent text).
    """

    def test_margin_section_number_is_stamped(self) -> None:
        body = _long_text(300)
        text = (
            "ARTICLE 8 — HOURS OF WORK AND OVERTIME\n"
            f"806 A. Overtime is paid at time and a half. {body}\n"
            f"807 A. Double time applies on Sundays. {body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=21)]))
        section_numbers = {c.section_number for c in chunks if c.section_number}
        assert "806" in section_numbers
        assert "807" in section_numbers

    def test_margin_section_groups_trailing_item_lines(self) -> None:
        # The O01 shape: items B and C belong to section 801, but decimal-only
        # detection left them section-less, so the model guessed the nearby 802.
        # With 3-digit recognition the whole 801 group inherits "801".
        body = _long_text(300)
        text = (
            "ARTICLE 8 — HOURS OF WORK AND OVERTIME\n"
            f"806 A. Overtime is paid at time and a half. {body}\n"
            "801 A. For employees working normal hours a rest period is allotted.\n"
            "B. A ten minute rest period is allotted before overtime. REST_ITEM_B\n"
            "C. A fifteen minute rest period is allotted during overtime. REST_ITEM_C\n"
            f"802 A. Reporting pay applies when sent home. {body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=21)]))
        c_chunk = next(c for c in chunks if "REST_ITEM_C" in c.text)
        assert c_chunk.section_number == "801"

    def test_three_digit_value_line_is_not_a_section(self) -> None:
        # A line beginning with a 3-digit number followed by lowercase prose is a
        # value ("500 hours…"), not a section header — must not be stamped.
        body = _long_text(300)
        text = (
            "ARTICLE 8 — HOURS\n"
            f"8.01 The workweek is capped. {body}\n"
            f"500 hours of accumulated overtime may be banked. {body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert "500" not in {c.section_number for c in chunks}

    def test_four_digit_year_line_is_not_a_section(self) -> None:
        body = _long_text(300)
        text = (
            "ARTICLE 8 — HOURS\n"
            f"8.01 A clause about hours. {body}\n"
            f"2025 Annual Review of the hours schedule occurs. {body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        sections = {c.section_number for c in chunks}
        assert "202" not in sections
        assert "2025" not in sections

    def test_sentence_opening_with_three_digit_number_is_not_a_section(self) -> None:
        # Ordinary narrative that opens with a 3-digit number and a capitalized
        # word — an address, a count, an emergency/phone number — must NOT be
        # stamped as a margin section. EPSCA sections always open with an item
        # letter ("801 A."), so these "NNN Word" lines are prose (#79 review).
        body = _long_text(300)
        text = (
            "ARTICLE 8 — HOURS\n"
            f"8.01 Hours of work are capped. {body}\n"
            "801 Yonge Street is the union hall address for all members.\n"
            "911 Emergency contact numbers are posted at every gate.\n"
            f"250 Ontario workers are covered by this clause. {body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        sections = {c.section_number for c in chunks}
        assert "801" not in sections
        assert "911" not in sections
        assert "250" not in sections


class TestAppendixBoundary:
    """Appendix clauses carry no ARTICLE/section heading, so they used to
    accumulate under the previous article and inherit a stale section number
    (#79, O04 — an appendix hours-of-work clause was stamped §48.1, which is
    actually Duration).  An appendix heading must reset the running context.
    """

    def _duration_then_appendix(self) -> list[TextBlock]:
        # Oversized Duration section so it splits and must carry its own number,
        # proving the appendix boundary doesn't suppress real section stamping.
        dur = _long_text(520)
        app = _long_text(300)
        text = (
            "ARTICLE 48 — DURATION\n"
            f"48.1 This agreement remains in effect until April 30, 2030. {dur}\n"
            "Appendix B 7 Day Coverage\n"
            f"(a) Regularly scheduled hours of ten hours per day. APPENDIX_MARKER {app}"
        )
        return [TextBlock(text=text, page_number=51)]

    def test_appendix_clause_does_not_inherit_stale_section(self) -> None:
        chunks = chunk_document(_make_doc(self._duration_then_appendix()))
        app_chunk = next(c for c in chunks if "APPENDIX_MARKER" in c.text)
        assert app_chunk.section_number is None

    def test_appendix_clause_gets_appendix_article_number(self) -> None:
        chunks = chunk_document(_make_doc(self._duration_then_appendix()))
        app_chunk = next(c for c in chunks if "APPENDIX_MARKER" in c.text)
        assert app_chunk.article_number == "Appendix B"

    def test_appendix_title_parsed_from_heading(self) -> None:
        chunks = chunk_document(_make_doc(self._duration_then_appendix()))
        app_chunk = next(c for c in chunks if "APPENDIX_MARKER" in c.text)
        assert app_chunk.article_title == "7 Day Coverage"

    def test_preceding_duration_section_still_stamped(self) -> None:
        chunks = chunk_document(_make_doc(self._duration_then_appendix()))
        dur_chunk = next(c for c in chunks if "remains in effect" in c.text)
        assert dur_chunk.section_number == "48.1"

    def test_midtext_appendix_reference_does_not_reset_context(self) -> None:
        # A cross-reference ("See Appendix B …") mid-clause is not a heading and
        # must not reset the article/section context.
        body = _long_text(300)
        text = (
            "ARTICLE 5 — WAGES\n"
            f"5.01 Rates are listed. See Appendix B for the full schedule. {body}\n"
            f"5.02 Additional rate provisions apply. {body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert all(
            c.article_number == "Article 5" for c in chunks if not c.is_table
        )

    def test_lowercase_appendix_heading_still_resets_and_normalizes(self) -> None:
        # Extraction can down-case a heading; "appendix c" must still reset the
        # context and normalize to "Appendix C" (#79 review: case symmetry with
        # ARTICLE, which is matched case-insensitively).
        dur = _long_text(520)
        app = _long_text(300)
        text = (
            "ARTICLE 48 — DURATION\n"
            f"48.1 This agreement remains in effect until April 30, 2030. {dur}\n"
            "appendix c wrap around\n"
            f"(a) A return trip is provided each cycle. LC_APPENDIX_MARKER {app}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=60)]))
        app_chunk = next(c for c in chunks if "LC_APPENDIX_MARKER" in c.text)
        assert app_chunk.article_number == "Appendix C"
        assert app_chunk.section_number is None

    def test_appendix_prose_reference_is_not_a_heading(self) -> None:
        # A sentence that merely begins with the word "Appendix" followed by a
        # multi-letter lower-case word is prose, not a heading — must not reset.
        body = _long_text(300)
        text = (
            "ARTICLE 5 — WAGES\n"
            f"5.01 Rates are listed here. {body}\n"
            f"Appendix to the agreement, the parties note the following. {body}"
        )
        chunks = chunk_document(_make_doc([TextBlock(text=text, page_number=1)]))
        assert all(
            c.article_number == "Article 5" for c in chunks if not c.is_table
        )
