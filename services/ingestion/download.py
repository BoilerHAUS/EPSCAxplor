"""
Stage 1: Download — fetch PDFs from EPSCA and store locally.

Downloads all documents listed in corpus_manifest.yaml into the corpus/
directory, organised as corpus/{union-slug}/{document_type}/{filename}.

Idempotent: files that already exist on disk are skipped (not re-downloaded).
Entries with missing or placeholder source_url values are skipped with status
NO_URL and must be placed manually before running the pipeline.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import httpx
import yaml

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
CORPUS_MANIFEST = _HERE / "corpus_manifest.yaml"
CORPUS_DIR = _HERE / "corpus"


class DownloadStatus(StrEnum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"    # file already present on disk — hash recorded
    NO_URL = "no_url"      # source_url absent or placeholder — manual placement needed
    FAILED = "failed"      # network or HTTP error


@dataclass(frozen=True)
class DownloadResult:
    source_filename: str
    status: DownloadStatus
    file_hash: str | None = None
    error: str | None = None


def union_slug(union_name: str) -> str:
    """Convert a union display name to a lowercase-kebab directory slug."""
    return union_name.lower().replace(" ", "-")


def resolve_corpus_path(entry: dict[str, str], corpus_dir: Path) -> Path:
    """Return the target filesystem path for a corpus manifest entry."""
    slug = union_slug(entry["union_name"])
    return corpus_dir / slug / entry["document_type"] / entry["source_filename"]


def compute_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def download_document(
    entry: dict[str, str],
    corpus_dir: Path,
    client: httpx.AsyncClient,
) -> DownloadResult:
    """
    Download a single document from its source_url, or skip if already present.

    Args:
        entry:      A corpus manifest document entry (dict).
        corpus_dir: Root directory for downloaded corpus files.
        client:     An active httpx.AsyncClient for HTTP requests.

    Returns:
        DownloadResult describing the outcome.
    """
    # Use .get() so a malformed entry doesn't abort the whole pipeline
    source_filename = entry.get("source_filename", "<unknown>")
    source_url = entry.get("source_url", "")

    if not source_url or source_url.startswith("PLACEHOLDER"):
        logger.info("No URL for %s — skipping (manual placement required)", source_filename)
        return DownloadResult(source_filename=source_filename, status=DownloadStatus.NO_URL)

    try:
        target = resolve_corpus_path(entry, corpus_dir)

        if target.exists():
            file_hash = compute_sha256(target)
            logger.info("Already present: %s (sha256=%.8s…)", source_filename, file_hash)
            return DownloadResult(
                source_filename=source_filename,
                status=DownloadStatus.SKIPPED,
                file_hash=file_hash,
            )

        logger.info("Downloading %s", source_filename)
        response = await client.get(source_url, follow_redirects=True)
        response.raise_for_status()
        target.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to a temp file then rename so a crash mid-write
        # does not leave a partial file that would be treated as complete on retry.
        tmp = target.with_suffix(".tmp")
        try:
            tmp.write_bytes(response.content)
            tmp.rename(target)
        finally:
            tmp.unlink(missing_ok=True)

        file_hash = compute_sha256(target)
        logger.info("Downloaded  %s (sha256=%.8s…)", source_filename, file_hash)
        return DownloadResult(
            source_filename=source_filename,
            status=DownloadStatus.DOWNLOADED,
            file_hash=file_hash,
        )
    except (httpx.HTTPError, KeyError) as exc:
        logger.error("Failed to download %s: %s", source_filename, exc)
        return DownloadResult(
            source_filename=source_filename,
            status=DownloadStatus.FAILED,
            error=str(exc),
        )


async def run_download(
    manifest_path: Path = CORPUS_MANIFEST,
    corpus_dir: Path = CORPUS_DIR,
) -> list[DownloadResult]:
    """
    Run the download stage for all documents in the corpus manifest.

    Args:
        manifest_path: Path to corpus_manifest.yaml.
        corpus_dir:    Root directory for downloaded corpus files.

    Returns:
        A list of DownloadResult, one per manifest entry.
    """
    with manifest_path.open() as f:
        manifest = yaml.safe_load(f) or {}

    documents: list[dict[str, str]] = manifest.get("documents", [])

    async with httpx.AsyncClient(timeout=120.0) as client:
        results = []
        for entry in documents:
            result = await download_document(entry, corpus_dir, client)
            results.append(result)

    return results
