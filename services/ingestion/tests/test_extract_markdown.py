"""Tests for extract_markdown() — Markdown-aware extraction path in extract.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from extract import ExtractedDocument, TableBlock, TextBlock

SIMPLE_TABLE_MD = """\
## Journeyperson Rates

| Classification | Effective Date | Hourly Rate |
|---|---|---|
| Journeyperson | 2025-01-01 | $43.98 |
| Apprentice 1st | 2025-01-01 | $21.99 |
"""

HEADERS_MD = """\
## Section One

Some text here.

## Section Two

More text here.
"""

PAGE_COMMENT_MD = """\
## Wage Rates
<!-- page: 1 -->
Some content on page 1.
<!-- page: 2 -->
More content on page 2.
"""

MALFORMED_TABLE_MD = """\
## Bad Table

| Col1 | Col2 |
This is not a separator row.
| data | data |
"""

CONSECUTIVE_HEADERS_MD = """\
## Header One

## Header Two

Content under two.
"""

MULTI_TABLE_MD = """\
## Journeyperson Rates

| Classification | Rate |
|---|---|
| Journeyperson | $43.98 |

## Apprentice Rates

| Year | Rate |
|---|---|
| 1st Year | $21.99 |
| 2nd Year | $26.39 |
"""

# Pathological IBEW-style: all rate rows crammed into one cell via <br> tags.
IBEW_BR_TABLE_MD = """\
## Wage Schedule

| Classification | Effective May 1, 2025 |
|---|---|
| Journeyperson: $52.34/hr<br>Apprentice 1st Period: $26.17/hr<br> \
Apprentice 2nd Period: $31.40/hr<br>Apprentice 3rd Period: $36.64/hr | \
IBEW Local 353 |
"""


class TestExtractMarkdownBasic:
    def test_returns_extracted_document(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "doc.md"
        md_file.write_text(SIMPLE_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=3)

        assert isinstance(doc, ExtractedDocument)
        assert doc.source_path == md_file
        assert doc.page_count == 3

    def test_pipe_table_produces_table_block(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "wage.md"
        md_file.write_text(SIMPLE_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        table_blocks = [b for b in doc.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) >= 1

    def test_pipe_table_block_has_header_and_data_rows(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "wage.md"
        md_file.write_text(SIMPLE_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        table_blocks = [b for b in doc.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) >= 1
        first_table = table_blocks[0]
        # Header row + 2 data rows = 3 rows total (separator row excluded)
        assert len(first_table.rows) == 3
        assert "Classification" in first_table.rows[0]

    def test_table_cell_values_preserved(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "wage.md"
        md_file.write_text(SIMPLE_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        table_blocks = [b for b in doc.blocks if isinstance(b, TableBlock)]
        all_cells = [cell for row in table_blocks[0].rows for cell in row]
        assert "$43.98" in all_cells

    def test_headers_produce_text_blocks(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "headers.md"
        md_file.write_text(HEADERS_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        text_blocks = [b for b in doc.blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) >= 2

    def test_empty_markdown_produces_empty_document(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "empty.md"
        md_file.write_text("", encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        assert doc.blocks == []
        assert doc.page_count == 1

    def test_multiple_tables_each_produce_table_block(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "multi.md"
        md_file.write_text(MULTI_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=2)

        table_blocks = [b for b in doc.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) == 2


class TestExtractMarkdownPageComments:
    def test_page_comment_does_not_appear_in_text_block(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "pages.md"
        md_file.write_text(PAGE_COMMENT_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=2)

        for block in doc.blocks:
            if isinstance(block, TextBlock):
                assert "<!-- page:" not in block.text

    def test_page_comment_updates_page_number(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "pages.md"
        md_file.write_text(PAGE_COMMENT_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=2)

        page_numbers = {b.page_number for b in doc.blocks}
        assert 2 in page_numbers


class TestExtractMarkdownEdgeCases:
    def test_malformed_table_falls_back_to_text_block(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "malformed.md"
        md_file.write_text(MALFORMED_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        table_blocks = [b for b in doc.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) == 0

    def test_consecutive_headers_produce_separate_blocks(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "consecutive.md"
        md_file.write_text(CONSECUTIVE_HEADERS_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        text_blocks = [b for b in doc.blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) >= 2

    def test_raises_file_not_found_for_missing_file(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        with pytest.raises(FileNotFoundError):
            extract_markdown(tmp_path / "nonexistent.md", page_count=1)

    def test_br_tags_expanded_before_parsing(self, tmp_path: Path) -> None:
        """IBEW PDFs produce <br>-delimited cells; expansion must surface rate rows."""
        from extract import extract_markdown

        md_file = tmp_path / "ibew_wage.md"
        md_file.write_text(IBEW_BR_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        all_text = " ".join(
            b.text if isinstance(b, TextBlock) else " ".join(c for row in b.rows for c in row)
            for b in doc.blocks
        )
        assert "$52.34" in all_text
        assert "$26.17" in all_text
        assert "$31.40" in all_text
        assert "$36.64" in all_text

    def test_br_tags_not_present_in_output(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "ibew_wage.md"
        md_file.write_text(IBEW_BR_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        all_text = " ".join(
            b.text if isinstance(b, TextBlock) else " ".join(c for row in b.rows for c in row)
            for b in doc.blocks
        )
        assert "<br>" not in all_text

    def test_table_block_is_frozen(self, tmp_path: Path) -> None:
        from extract import extract_markdown

        md_file = tmp_path / "wage.md"
        md_file.write_text(SIMPLE_TABLE_MD, encoding="utf-8")
        doc = extract_markdown(md_file, page_count=1)

        table_blocks = [b for b in doc.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) >= 1
        with pytest.raises((AttributeError, TypeError)):
            table_blocks[0].rows = ()  # type: ignore[misc]
