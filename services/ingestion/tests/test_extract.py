"""Tests for extract.py — Stage 2 of the ingestion pipeline."""

from pathlib import Path
from unittest.mock import patch

import pytest

from extract import ExtractedDocument, TableBlock, TableRows, TextBlock, extract_pdf
from tests.conftest import make_mock_page, make_mock_pdf


class TestExtractPdf:
    def test_raises_file_not_found_for_missing_pdf(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.pdf"
        with pytest.raises(FileNotFoundError, match="nonexistent.pdf"):
            extract_pdf(missing)

    def test_returns_extracted_document(self, tmp_pdf: Path) -> None:
        pages = [make_mock_page(1, "Some text")]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)
        assert isinstance(result, ExtractedDocument)

    def test_page_count_is_populated(self, tmp_pdf: Path) -> None:
        pages = [make_mock_page(1, "Page 1"), make_mock_page(2, "Page 2")]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)
        assert result.page_count == 2

    def test_source_path_is_set(self, tmp_pdf: Path) -> None:
        pages = [make_mock_page(1, "Text")]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)
        assert result.source_path == tmp_pdf


class TestPageNumberPreservation:
    def test_text_block_carries_page_number(self, tmp_pdf: Path) -> None:
        pages = [
            make_mock_page(1, "First page content"),
            make_mock_page(2, "Second page content"),
        ]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        text_blocks = [b for b in result.blocks if isinstance(b, TextBlock)]
        page_numbers = {b.page_number for b in text_blocks}
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_page_numbers_match_pdfplumber_page_number(self, tmp_pdf: Path) -> None:
        # pdfplumber uses 1-indexed page numbers; we must pass them through unchanged
        pages = [make_mock_page(page_number=3, text="Deep into a document")]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        text_blocks = [b for b in result.blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) == 1
        assert text_blocks[0].page_number == 3

    def test_table_block_carries_page_number(self, tmp_pdf: Path) -> None:
        table_data = [["Classification", "Rate"], ["Journeyperson", "$45.00"]]
        pages = [make_mock_page(5, "Wage Schedule", tables=[table_data])]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        table_blocks = [b for b in result.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) == 1
        assert table_blocks[0].page_number == 5


class TestTableFlagging:
    def test_table_block_is_flagged_as_table(self, tmp_pdf: Path) -> None:
        table_data = [["Col A", "Col B"], ["1", "2"]]
        pages = [make_mock_page(1, "Some text", tables=[table_data])]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        table_blocks = [b for b in result.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) == 1
        assert table_blocks[0].is_table is True

    def test_text_block_is_not_flagged_as_table(self, tmp_pdf: Path) -> None:
        pages = [make_mock_page(1, "ARTICLE 12 — Overtime")]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        text_blocks = [b for b in result.blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) == 1
        assert text_blocks[0].is_table is False

    def test_page_with_table_produces_both_text_and_table_blocks(self, tmp_pdf: Path) -> None:
        table_data = [["Article", "Rate"], ["12.01", "$45.00"]]
        pages = [make_mock_page(1, "ARTICLE 12 Overtime\n12.01 Hourly Rate", tables=[table_data])]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        text_blocks = [b for b in result.blocks if isinstance(b, TextBlock)]
        table_blocks = [b for b in result.blocks if isinstance(b, TableBlock)]
        assert len(text_blocks) == 1
        assert len(table_blocks) == 1

    def test_table_rows_are_preserved_as_tuples(self, tmp_pdf: Path) -> None:
        table_data = [
            ["Classification", "Hourly Rate", "Vacation Pay"],
            ["Journeyperson", "$45.00", "10%"],
            ["Apprentice", "$36.00", "10%"],
        ]
        pages = [make_mock_page(1, "Wage Schedule", tables=[table_data])]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        table_blocks = [b for b in result.blocks if isinstance(b, TableBlock)]
        # rows are stored as tuple-of-tuples for true immutability
        expected: TableRows = tuple(tuple(row) for row in table_data)
        assert table_blocks[0].rows == expected

    def test_table_rows_are_immutable(self, tmp_pdf: Path) -> None:
        table_data = [["A", "B"], ["1", "2"]]
        pages = [make_mock_page(1, "Text", tables=[table_data])]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        block = next(b for b in result.blocks if isinstance(b, TableBlock))
        # frozen=True + tuple rows: both attribute reassignment and in-place
        # mutation should be impossible
        with pytest.raises((TypeError, AttributeError)):
            block.rows = ()  # type: ignore[misc]

    def test_multiple_tables_on_one_page(self, tmp_pdf: Path) -> None:
        table1 = [["A", "B"], ["1", "2"]]
        table2 = [["X", "Y"], ["3", "4"]]
        pages = [make_mock_page(1, "Page with two tables", tables=[table1, table2])]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        table_blocks = [b for b in result.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) == 2


class TestErrorHandling:
    def test_raises_value_error_for_corrupt_pdf(self, tmp_pdf: Path) -> None:
        with patch("extract.pdfplumber.open", side_effect=Exception("No /Root object!")):
            with pytest.raises(ValueError, match="Failed to parse PDF"):
                extract_pdf(tmp_pdf)

    def test_value_error_chains_original_exception(self, tmp_pdf: Path) -> None:
        original = Exception("PDFSyntaxError: unexpected token")
        with patch("extract.pdfplumber.open", side_effect=original):
            with pytest.raises(ValueError) as exc_info:
                extract_pdf(tmp_pdf)
        assert exc_info.value.__cause__ is original


class TestEdgeCases:
    def test_empty_page_produces_no_text_block(self, tmp_pdf: Path) -> None:
        pages = [make_mock_page(1, None), make_mock_page(2, "")]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        text_blocks = [b for b in result.blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) == 0

    def test_whitespace_only_page_produces_no_text_block(self, tmp_pdf: Path) -> None:
        pages = [make_mock_page(1, "   \n\t  ")]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        text_blocks = [b for b in result.blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) == 0

    def test_multi_page_document_preserves_all_pages(self, tmp_pdf: Path) -> None:
        pages = [make_mock_page(i, f"Content of page {i}") for i in range(1, 6)]
        mock_pdf = make_mock_pdf(pages)
        with patch("extract.pdfplumber.open", return_value=mock_pdf):
            result = extract_pdf(tmp_pdf)

        text_blocks = [b for b in result.blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) == 5
        extracted_page_nums = sorted(b.page_number for b in text_blocks)
        assert extracted_page_nums == [1, 2, 3, 4, 5]
