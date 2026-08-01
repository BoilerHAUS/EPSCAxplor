"""Purge superseded documents from Postgres + Qdrant (issue #178).

When EPSCA reissues a wage schedule its manifest ``source_filename`` changes
(e.g. ``"... - May 1, 2025.pdf"`` → ``"... - May 01, 2026.pdf"``).  ``store.py``
keys the Postgres ``documents`` row on ``source_filename`` and each Qdrant point
on the resulting ``document_id``, so re-ingesting under the NEW filename inserts
a fresh row/points and leaves the OLD document's row and chunks **orphaned** —
the stale rates keep being retrieved.  This script removes those superseded
documents by their (old) ``source_filename``: it deletes each matched document's
Qdrant points (by ``document_id``) and then its Postgres row.

Reissues that keep the same ``source_filename`` (e.g. an upstream file rename
with identical content) update in place and need no purge — only filename
*changes* orphan the prior document.

Idempotent: a ``source_filename`` already absent from ``documents`` is reported
and skipped.  Use ``--dry-run`` to preview without deleting.

Environment variables (mirrors store.py):
    QDRANT_URL:     Base URL for Qdrant.  Default: http://127.0.0.1:6333
    QDRANT_API_KEY: Qdrant **read-write** key (deletes points); blank ⇒ keyless.
    POSTGRES_DSN:   asyncpg-compatible connection string (required).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass, field

import asyncpg
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

from store import QDRANT_COLLECTION, _normalize_qdrant_api_key

logger = logging.getLogger(__name__)

QDRANT_URL: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY: str | None = _normalize_qdrant_api_key(os.getenv("QDRANT_API_KEY"))
POSTGRES_DSN: str = os.getenv("POSTGRES_DSN", "")


@dataclass
class PurgeResult:
    """Outcome of a purge run."""

    # (source_filename, document_id) for each document removed (or, in a dry
    # run, that would be removed).
    purged: list[tuple[str, str]] = field(default_factory=list)
    # Requested source_filenames not present in `documents` (already gone).
    not_found: list[str] = field(default_factory=list)

    @property
    def purged_count(self) -> int:
        return len(self.purged)


async def _resolve_document_ids(
    conn: asyncpg.Connection, source_filenames: Sequence[str]
) -> list[tuple[str, object]]:
    """Return ``(source_filename, id)`` for each name present in ``documents``."""
    rows = await conn.fetch(
        "SELECT id, source_filename FROM documents "
        "WHERE source_filename = ANY($1::text[])",
        list(source_filenames),
    )
    return [(row["source_filename"], row["id"]) for row in rows]


async def purge_documents(
    source_filenames: Sequence[str],
    *,
    dry_run: bool = False,
    qdrant_url: str = QDRANT_URL,
    qdrant_api_key: str | None = QDRANT_API_KEY,
    postgres_dsn: str = POSTGRES_DSN,
) -> PurgeResult:
    """Delete the named documents' Qdrant points and Postgres rows.

    Qdrant points are deleted before the Postgres row so a failure mid-way
    leaves the row (and thus a retryable ``document_id``) intact rather than
    orphaning chunks with no owning row.

    Raises:
        RuntimeError: if ``postgres_dsn`` is empty.
    """
    if not postgres_dsn:
        raise RuntimeError(
            "POSTGRES_DSN environment variable is required; "
            "set it to your asyncpg connection string."
        )

    result = PurgeResult()
    if not source_filenames:
        return result

    async with asyncpg.create_pool(postgres_dsn) as pool:
        async with pool.acquire() as conn:
            matches = await _resolve_document_ids(conn, source_filenames)
            found = {name for name, _ in matches}
            result.not_found = [n for n in source_filenames if n not in found]

            if not matches:
                return result

            qdrant = AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            try:
                for source_filename, document_id in matches:
                    doc_id = str(document_id)
                    if dry_run:
                        logger.info(
                            "[DRY-RUN] would purge %s (document_id=%s)",
                            source_filename,
                            doc_id,
                        )
                    else:
                        await qdrant.delete(
                            collection_name=QDRANT_COLLECTION,
                            points_selector=FilterSelector(
                                filter=Filter(
                                    must=[
                                        FieldCondition(
                                            key="document_id",
                                            match=MatchValue(value=doc_id),
                                        )
                                    ]
                                )
                            ),
                        )
                        await conn.execute(
                            "DELETE FROM documents WHERE id = $1", document_id
                        )
                        logger.info(
                            "Purged %s (document_id=%s)", source_filename, doc_id
                        )
                    result.purged.append((source_filename, doc_id))
            finally:
                await qdrant.close()

    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Purge superseded documents from Postgres + Qdrant (#178)"
    )
    parser.add_argument(
        "source_filenames",
        nargs="+",
        metavar="SOURCE_FILENAME",
        help="Exact source_filename(s) of the superseded document(s) to purge.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would be purged without deleting anything.",
    )
    args = parser.parse_args()

    result = asyncio.run(purge_documents(args.source_filenames, dry_run=args.dry_run))

    for name in result.not_found:
        logger.warning("Not found in documents (skipped): %s", name)
    logger.info(
        "%s %d document(s); %d not found.",
        "Would purge" if args.dry_run else "Purged",
        result.purged_count,
        len(result.not_found),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
