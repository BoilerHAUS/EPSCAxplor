"""Tests for convert.py — PDF→Markdown conversion stage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
