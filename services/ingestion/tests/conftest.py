"""Shared pytest fixtures for ingestion pipeline tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def make_mock_page(
    page_number: int,
    text: str | None,
    tables: list[list[list[str | None]]] | None = None,
) -> MagicMock:
    """Build a mock pdfplumber Page object."""
    page = MagicMock()
    page.page_number = page_number
    page.extract_text.return_value = text
    page.extract_tables.return_value = tables or []
    return page


def make_mock_pdf(pages: list[MagicMock]) -> MagicMock:
    """Build a mock pdfplumber PDF context manager."""
    mock_pdf = MagicMock()
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdf.__exit__.return_value = False
    mock_pdf.pages = pages
    return mock_pdf


@pytest.fixture()
def tmp_pdf(tmp_path: Path) -> Path:
    """A temporary file that exists but is not a real PDF (used for path-exist tests)."""
    p = tmp_path / "test.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    return p
