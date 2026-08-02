"""Tests for convert.py — PDF→Markdown conversion stage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

FAKE_MARKDOWN = (
    "## Journeyperson Rates\n\n"
    "| Classification | Effective Date | Hourly Rate |\n"
    "|---|---|---|\n"
    "| Journeyperson | 2025-01-01 | $43.98 |\n"
)


class TestConvertPdfCreatesOutput:
    def test_creates_md_file(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN):  # type: ignore[attr-defined]
            result = convert_pdf(pdf, tmp_path / "cache")

        assert result.markdown_path.exists()
        assert result.markdown_path.suffix == ".md"

    def test_output_is_utf8(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")
        unicode_md = (
            "## Tarifs — Journalier\n| Poste | Taux |\n|---|---|\n| Journalier | 43,98\u00a0$ |"
        )

        with patch("convert._convert_with_pymupdf4llm", return_value=unicode_md):  # type: ignore[attr-defined]
            result = convert_pdf(pdf, tmp_path / "cache")

        content = result.markdown_path.read_text(encoding="utf-8")
        assert "Journalier" in content

    def test_writes_sidecar_meta(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN):  # type: ignore[attr-defined]
            result = convert_pdf(pdf, tmp_path / "cache")

        sidecar = result.markdown_path.parent / (result.markdown_path.name + ".meta.json")
        assert sidecar.exists()
        meta = json.loads(sidecar.read_text())
        assert "source_sha256" in meta
        assert "engine" in meta
        assert "engine_version" in meta
        assert meta["engine"] == "pymupdf4llm"

    def test_sha256_in_meta_matches_source(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        content = b"%PDF-1.4 fake pdf content"
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(content)
        expected_sha = hashlib.sha256(content).hexdigest()

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN):  # type: ignore[attr-defined]
            result = convert_pdf(pdf, tmp_path / "cache")

        assert result.source_sha256 == expected_sha
        sidecar = result.markdown_path.parent / (result.markdown_path.name + ".meta.json")
        meta = json.loads(sidecar.read_text())
        assert meta["source_sha256"] == expected_sha

    def test_returned_dataclass_fields(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN):  # type: ignore[attr-defined]
            result = convert_pdf(pdf, tmp_path / "cache")

        assert result.source_path == pdf
        assert result.engine == "pymupdf4llm"
        assert isinstance(result.engine_version, str)
        assert len(result.engine_version) > 0
        assert result.markdown == FAKE_MARKDOWN


class TestConvertPdfCaching:
    def test_skips_when_cache_valid(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN) as mock_backend:  # type: ignore[attr-defined]
            convert_pdf(pdf, tmp_path / "cache")
            convert_pdf(pdf, tmp_path / "cache")

        assert mock_backend.call_count == 1

    def test_rebuilds_when_sha_changes(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 original content")

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN) as mock_backend:  # type: ignore[attr-defined]
            convert_pdf(pdf, tmp_path / "cache")
            pdf.write_bytes(b"%PDF-1.4 CHANGED content after edit")
            convert_pdf(pdf, tmp_path / "cache")

        assert mock_backend.call_count == 2

    def test_force_bypasses_cache(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN) as mock_backend:  # type: ignore[attr-defined]
            convert_pdf(pdf, tmp_path / "cache")
            convert_pdf(pdf, tmp_path / "cache", force=True)

        assert mock_backend.call_count == 2


class TestConvertPdfAtomicWrite:
    def test_no_partial_md_file_on_backend_crash(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")
        cache_dir = tmp_path / "cache"

        with patch("convert._convert_with_pymupdf4llm", side_effect=RuntimeError("crash")):  # type: ignore[attr-defined]
            with pytest.raises(RuntimeError):
                convert_pdf(pdf, cache_dir)

        md_files = list(cache_dir.glob("*.md")) if cache_dir.exists() else []
        assert md_files == []


class TestConvertPdfErrors:
    def test_raises_file_not_found_for_missing_pdf(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        with pytest.raises(FileNotFoundError):
            convert_pdf(tmp_path / "nonexistent.pdf", tmp_path / "cache")

    def test_raises_value_error_for_unknown_engine(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")

        with pytest.raises(ValueError, match="Unknown engine"):
            convert_pdf(pdf, tmp_path / "cache", engine="gibberish")


class TestConvertPdfMarkdownContent:
    def test_preserves_pipe_tables_in_returned_markdown(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "wage_schedule.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")
        table_md = (
            "## Journeyperson Rates\n\n"
            "| Classification | Effective Date | Hourly Rate |\n"
            "|---|---|---|\n"
            "| Journeyperson | 2025-01-01 | $43.98 |\n"
        )

        with patch("convert._convert_with_pymupdf4llm", return_value=table_md):  # type: ignore[attr-defined]
            result = convert_pdf(pdf, tmp_path / "cache")

        assert "|" in result.markdown
        assert "---" in result.markdown
        assert "$43.98" in result.markdown


# ─── Two-column form engine (#179) ────────────────────────────────────────────
#
# The geometry helpers are pure functions over word boxes, so these tests build
# synthetic pages instead of committing a binary PDF fixture.  Coordinates
# mirror the real Teamsters "Union Dues" form: a left column starting at x=53
# and a right column starting at x=283, ~9pt line spacing.


def _word(x0: float, top: float, text: str, width: float = 60.0) -> dict[str, object]:
    """A pdfplumber-shaped word box."""
    return {"x0": x0, "x1": x0 + width, "top": top, "text": text}


class TestGroupWordsIntoLines:
    def test_words_on_same_baseline_form_one_line_ordered_by_x(self) -> None:
        from convert import _group_words_into_lines

        lines = _group_words_into_lines(
            [_word(283, 152, "879"), _word(53, 152, "Local")]
        )

        assert len(lines) == 1
        assert lines[0].text == "Local 879"

    def test_sub_point_baseline_jitter_stays_one_line(self) -> None:
        # Real extractions report the same visual line with ~1pt of jitter.
        from convert import _group_words_into_lines

        lines = _group_words_into_lines(
            [_word(53, 293, "Email:"), _word(283, 294, "Ottawa,")]
        )

        assert len(lines) == 1

    def test_distinct_baselines_form_separate_lines_top_down(self) -> None:
        from convert import _group_words_into_lines

        lines = _group_words_into_lines(
            [_word(53, 161, "rate"), _word(53, 152, "Local")]
        )

        assert [line.text for line in lines] == ["Local", "rate"]


class TestLineGutters:
    def test_wide_blank_run_is_a_gutter(self) -> None:
        from convert import _MIN_GUTTER_PT, _group_words_into_lines, _line_gutters

        line = _group_words_into_lines(
            [_word(53, 152, "left", width=80), _word(283, 152, "right", width=80)]
        )[0]

        gutters = _line_gutters(line)

        assert len(gutters) == 1
        assert gutters[0][1] - gutters[0][0] >= _MIN_GUTTER_PT

    def test_ordinary_word_spacing_is_not_a_gutter(self) -> None:
        from convert import _group_words_into_lines, _line_gutters

        line = _group_words_into_lines(
            [_word(53, 152, "Teamsters", width=50), _word(106, 152, "Local", width=30)]
        )[0]

        assert _line_gutters(line) == []


class TestColumnSegments:
    """The property that matters: a two-column card keeps its own heading."""

    def _dues_grid(self) -> list[Any]:
        from convert import _group_words_into_lines

        return _group_words_into_lines(
            [
                _word(53, 152, "Teamsters Local 230", width=83),
                _word(283, 152, "Teamsters Local 879", width=83),
                _word(53, 161, "2.5x the hourly rate plus $7.00", width=163),
                _word(283, 161, "3x the hourly rate", width=66),
            ]
        )

    def test_each_local_is_followed_by_its_own_rate(self) -> None:
        from convert import _column_segments

        text = "\n".join(_column_segments(self._dues_grid()))

        assert "Teamsters Local 230\n2.5x the hourly rate plus $7.00" in text
        assert "Teamsters Local 879\n3x the hourly rate" in text

    def test_columns_are_not_interleaved(self) -> None:
        from convert import _column_segments

        text = "\n".join(_column_segments(self._dues_grid()))

        # The failure mode this engine exists to prevent: reading across the
        # page pairs local 230 with local 879's formula.
        assert "Teamsters Local 230 Teamsters Local 879" not in text

    def test_single_column_lines_keep_document_order(self) -> None:
        from convert import _column_segments, _group_words_into_lines

        lines = _group_words_into_lines(
            [
                _word(53, 104, "UNION DUES", width=90),
                _word(53, 114, "Local Union Dues Checkoff -", width=140),
            ]
        )

        assert "\n".join(_column_segments(lines)).splitlines() == [
            "UNION DUES",
            "Local Union Dues Checkoff -",
        ]

    def test_lone_gutter_line_is_not_treated_as_columns(self) -> None:
        # A single spaced-out header line ("MAP CODE:   ISSUED:   REVISED:") is
        # not a column layout; splitting it would scatter the form header.
        from convert import _column_segments, _group_words_into_lines

        lines = _group_words_into_lines(
            [_word(53, 57, "MAP CODE:", width=46), _word(172, 57, "ISSUED:", width=40)]
        )

        assert "\n".join(_column_segments(lines)) == "MAP CODE: ISSUED:"

    def test_narrow_line_joins_the_column_it_sits_under(self) -> None:
        # The trailing "905-415-5139" phone line has no gutter of its own but
        # belongs to the left card, not to the page body.
        from convert import _column_segments, _group_words_into_lines

        lines = _group_words_into_lines(
            [
                _word(53, 152, "Local 230", width=83),
                _word(283, 152, "Local 879", width=83),
                _word(53, 161, "info@teamsters230.ca", width=100),
                _word(283, 161, "Stoney Creek, ON", width=90),
                _word(53, 170, "905-415-5139", width=60),
            ]
        )

        text = "\n".join(_column_segments(lines))

        assert "info@teamsters230.ca\n905-415-5139" in text

    def test_full_width_line_closes_the_band(self) -> None:
        from convert import _column_segments, _group_words_into_lines

        lines = _group_words_into_lines(
            [
                _word(53, 152, "Local 230", width=83),
                _word(283, 152, "Local 879", width=83),
                _word(53, 161, "2.5x plus $7.00", width=83),
                _word(283, 161, "3x the rate", width=83),
                _word(53, 175, "Dues are deducted from the Base Hourly Rate", width=500),
            ]
        )

        segments = "\n".join(_column_segments(lines))

        assert segments.endswith("Dues are deducted from the Base Hourly Rate")


class TestConvertWithColumnsEngine:
    def test_engine_is_selectable_and_routed(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "dues.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")
        md = "<!-- page: 1 -->\nTeamsters Local 230\n2.5x the hourly rate plus $7.00"

        with patch("convert._convert_with_columns", return_value=md):
            result = convert_pdf(pdf, tmp_path / "cache", engine="pdfplumber_columns")

        assert result.engine == "pdfplumber_columns"
        assert result.page_count == 1
        assert "2.5x the hourly rate plus $7.00" in result.markdown

    def test_pymupdf4llm_remains_the_default(self, tmp_path: Path) -> None:
        from convert import convert_pdf

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("convert._convert_with_pymupdf4llm", return_value=FAKE_MARKDOWN):
            result = convert_pdf(pdf, tmp_path / "cache")

        assert result.engine == "pymupdf4llm"


class _StubTable:
    """Minimal stand-in for a pdfplumber Table."""

    def __init__(
        self, bbox: tuple[float, float, float, float], rows: list[list[str | None]]
    ) -> None:
        self.bbox = bbox
        self._rows = rows

    def extract(self) -> list[list[str | None]]:
        return self._rows


class _StubPage:
    """Minimal stand-in for a pdfplumber Page."""

    def __init__(
        self, words: list[dict[str, object]], tables: list[_StubTable]
    ) -> None:
        self._words = words
        self._tables = tables

    def find_tables(self) -> list[_StubTable]:
        return self._tables

    def extract_words(self) -> list[dict[str, object]]:
        return self._words


class TestPageMarkdownTableBoundaries:
    """Words inside a table belong to that table's markdown — exactly once."""

    @staticmethod
    def _nested_page() -> _StubPage:
        # find_tables() can return a table nested inside another on ruled or
        # borderless layouts. The outer spans 100–300, the inner 150–200.
        return _StubPage(
            [
                _word(10, 50, "HEADER"),
                _word(10, 120, "INSIDE_OUTER_ABOVE_INNER"),
                _word(10, 250, "INSIDE_OUTER_BELOW_INNER"),
                _word(10, 350, "FOOTER"),
            ],
            [
                _StubTable((0, 100, 500, 300), [["A1", "A2"]]),
                _StubTable((0, 150, 500, 200), [["B1", "B2"]]),
            ],
        )

    def test_nested_table_does_not_leak_enclosing_rows_as_loose_text(self) -> None:
        from convert import _page_markdown

        result = _page_markdown(self._nested_page())

        # Regression guard: the inner table must not rewind the consumed
        # boundary, or the outer table's remaining words are emitted a second
        # time as body text — the same rows in two places, one uncited.
        assert "INSIDE_OUTER_BELOW_INNER" not in result
        assert "INSIDE_OUTER_ABOVE_INNER" not in result

    def test_text_outside_every_table_survives(self) -> None:
        from convert import _page_markdown

        result = _page_markdown(self._nested_page())

        assert "HEADER" in result
        assert "FOOTER" in result

    def test_both_tables_are_still_emitted(self) -> None:
        from convert import _page_markdown

        result = _page_markdown(self._nested_page())

        assert "|A1|A2|" in result
        assert "|B1|B2|" in result

    def test_sequential_tables_keep_the_text_between_them(self) -> None:
        from convert import _page_markdown

        page = _StubPage(
            [_word(10, 250, "BETWEEN")],
            [
                _StubTable((0, 100, 500, 200), [["A1"]]),
                _StubTable((0, 300, 500, 400), [["B1"]]),
            ],
        )

        result = _page_markdown(page)

        assert result.index("|A1|") < result.index("BETWEEN") < result.index("|B1|")


class TestTableMarkdownRaggedRows:
    def test_short_row_is_padded_to_the_header_width(self) -> None:
        from convert import _table_markdown

        result = _table_markdown([["Local", "Areas", "Note"], ["230", "Toronto"]])

        # A row narrower than the header would otherwise shift every later cell
        # under the wrong column once extract.py re-parses the pipe row.
        assert result.splitlines()[-1] == "|230|Toronto||"

    def test_long_row_is_truncated_to_the_header_width(self) -> None:
        from convert import _table_markdown

        result = _table_markdown([["Local", "Areas"], ["879", "Sarnia", "extra"]])

        assert result.splitlines()[-1] == "|879|Sarnia|"

    def test_empty_rows_produce_no_table(self) -> None:
        from convert import _table_markdown

        assert _table_markdown([]) == ""
