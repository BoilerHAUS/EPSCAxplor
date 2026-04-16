"""Tests for download.py — Stage 1 of the ingestion pipeline."""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx

from download import (
    DownloadStatus,
    compute_sha256,
    download_document,
    resolve_corpus_path,
    union_slug,
)


class TestUnionSlug:
    def test_lowercase_conversion(self) -> None:
        assert union_slug("IBEW") == "ibew"

    def test_spaces_become_hyphens(self) -> None:
        assert union_slug("Sheet Metal") == "sheet-metal"

    def test_already_lowercase_unchanged(self) -> None:
        assert union_slug("boilermakers") == "boilermakers"

    def test_mixed_case_with_spaces(self) -> None:
        assert union_slug("United Association") == "united-association"


class TestResolveCorpusPath:
    def test_path_structure(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW Generation- 2025-2030 Collective Agreement.pdf",
        }
        result = resolve_corpus_path(entry, tmp_path)
        filename = "IBEW Generation- 2025-2030 Collective Agreement.pdf"
        assert result == tmp_path / "ibew" / "primary_ca" / filename

    def test_nuclear_pa_path(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "Sheet Metal",
            "document_type": "nuclear_pa",
            "source_filename": "Sheet Metal Nuclear Project Agreement.pdf",
        }
        result = resolve_corpus_path(entry, tmp_path)
        filename = "Sheet Metal Nuclear Project Agreement.pdf"
        assert result == tmp_path / "sheet-metal" / "nuclear_pa" / filename


class TestComputeSha256:
    def test_known_hash(self, tmp_path: Path) -> None:
        content = b"hello world"
        f = tmp_path / "test.bin"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_sha256(f) == expected

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"content a")
        f2.write_bytes(b"content b")
        assert compute_sha256(f1) != compute_sha256(f2)

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        content = b"deterministic"
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert compute_sha256(f1) == compute_sha256(f2)


def _make_async_client(status_code: int = 200, content: bytes = b"%PDF fake") -> AsyncMock:
    """Build an AsyncMock httpx.AsyncClient that returns a successful response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.content = content
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    return mock_client


def _make_error_client(error: Exception) -> AsyncMock:
    """Build an AsyncMock httpx.AsyncClient that raises an error."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = error
    return mock_client


class TestDownloadDocument:
    async def test_downloads_file_to_correct_path(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW Gen CA.pdf",
            "source_url": "https://example.com/ibew.pdf",
        }
        client = _make_async_client()
        result = await download_document(entry, tmp_path, client)

        assert result.status == DownloadStatus.DOWNLOADED
        target = tmp_path / "ibew" / "primary_ca" / "IBEW Gen CA.pdf"
        assert target.exists()

    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "United Association",
            "document_type": "nuclear_pa",
            "source_filename": "UA NPA.pdf",
            "source_url": "https://example.com/ua-npa.pdf",
        }
        client = _make_async_client()
        await download_document(entry, tmp_path, client)

        target = tmp_path / "united-association" / "nuclear_pa" / "UA NPA.pdf"
        assert target.exists()

    async def test_returns_file_hash_on_success(self, tmp_path: Path) -> None:
        content = b"%PDF actual content"
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW.pdf",
            "source_url": "https://example.com/ibew.pdf",
        }
        client = _make_async_client(content=content)
        result = await download_document(entry, tmp_path, client)

        assert result.status == DownloadStatus.DOWNLOADED
        expected_hash = hashlib.sha256(content).hexdigest()
        assert result.file_hash == expected_hash

    async def test_skips_already_existing_file(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW.pdf",
            "source_url": "https://example.com/ibew.pdf",
        }
        target = tmp_path / "ibew" / "primary_ca" / "IBEW.pdf"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"%PDF existing")

        client = _make_async_client()
        result = await download_document(entry, tmp_path, client)

        assert result.status == DownloadStatus.SKIPPED
        client.get.assert_not_called()

    async def test_skip_returns_existing_file_hash(self, tmp_path: Path) -> None:
        content = b"%PDF existing content"
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW.pdf",
            "source_url": "https://example.com/ibew.pdf",
        }
        target = tmp_path / "ibew" / "primary_ca" / "IBEW.pdf"
        target.parent.mkdir(parents=True)
        target.write_bytes(content)

        client = _make_async_client()
        result = await download_document(entry, tmp_path, client)

        assert result.file_hash == hashlib.sha256(content).hexdigest()

    async def test_returns_no_url_for_missing_source_url(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW.pdf",
        }
        client = _make_async_client()
        result = await download_document(entry, tmp_path, client)

        assert result.status == DownloadStatus.NO_URL
        client.get.assert_not_called()

    async def test_returns_no_url_for_placeholder_url(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW.pdf",
            "source_url": "PLACEHOLDER - see https://www.epsca.org/resources",
        }
        client = _make_async_client()
        result = await download_document(entry, tmp_path, client)

        assert result.status == DownloadStatus.NO_URL

    async def test_returns_failed_on_http_error(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW.pdf",
            "source_url": "https://example.com/ibew.pdf",
        }
        client = _make_error_client(httpx.ConnectError("Connection refused"))
        result = await download_document(entry, tmp_path, client)

        assert result.status == DownloadStatus.FAILED
        assert result.file_hash is None
        assert result.error is not None

    async def test_returns_failed_on_http_status_error(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW.pdf",
            "source_url": "https://example.com/ibew.pdf",
        }
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(),
        )
        client = AsyncMock()
        client.get.return_value = mock_response

        result = await download_document(entry, tmp_path, client)

        assert result.status == DownloadStatus.FAILED

    async def test_source_filename_is_always_in_result(self, tmp_path: Path) -> None:
        entry = {
            "union_name": "IBEW",
            "document_type": "primary_ca",
            "source_filename": "IBEW Gen CA.pdf",
        }
        client = _make_async_client()
        result = await download_document(entry, tmp_path, client)
        assert result.source_filename == "IBEW Gen CA.pdf"

    async def test_malformed_entry_missing_required_key_returns_failed(
        self, tmp_path: Path
    ) -> None:
        # Missing union_name and document_type — resolve_corpus_path would KeyError
        entry = {
            "source_filename": "Mystery.pdf",
            "source_url": "https://example.com/mystery.pdf",
        }
        client = _make_async_client()
        result = await download_document(entry, tmp_path, client)
        assert result.status == DownloadStatus.FAILED
        assert result.error is not None
