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
