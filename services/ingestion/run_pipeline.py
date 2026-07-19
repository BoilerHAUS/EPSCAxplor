"""
Ingestion pipeline orchestrator.

Runs all six stages sequentially against every document in the corpus manifest,
or a single stage when --stage is specified.

Usage:
    python run_pipeline.py                   # runs all stages for all documents
    python run_pipeline.py --dry-run         # skips store (embed → /dev/null)
    python run_pipeline.py --stage download  # runs only the download stage
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_pipeline")

STAGES = ["download", "extract", "classify", "chunk", "embed", "store"]

_HERE = Path(__file__).parent
MD_CACHE_DIR = _HERE / "corpus_md"


# ─── Single-stage helpers ─────────────────────────────────────────────────────


async def _run_download() -> None:
    from download import run_download

    results = await run_download()
    for r in results:
        detail = r.file_hash or r.error or ""
        logger.info("[%s] %s — %s", r.status.value.upper(), r.source_filename, detail)


# ─── Full pipeline (per-document) ─────────────────────────────────────────────


async def _run_full_pipeline(dry_run: bool, doc_type_filter: str | None = None) -> None:
    """
    Run all stages end-to-end for every document found in the corpus.

    Download stage is skipped here (run it separately via --stage download).
    Remaining stages operate on every PDF already present in corpus/.
    """
    from chunk import Chunk, chunk_document

    import yaml

    from classify import ClassifiedDocument, classify
    from convert import convert_pdf
    from download import CORPUS_DIR, CORPUS_MANIFEST, resolve_corpus_path
    from embed import embed_chunks
    from epsca_wage_parser import (
        build_wage_chunks,
        epsca_wage_parser_enabled,
        parse_wage_schedule_pdf,
    )
    from extract import ExtractedDocument, extract_markdown, extract_pdf
    from store import store_document
    from wage_tables import is_wage_schedule_entry

    with CORPUS_MANIFEST.open() as f:
        manifest_data = yaml.safe_load(f) or {}
    entries = list(manifest_data.get("documents", []))

    if doc_type_filter:
        entries = [e for e in entries if e.get("document_type") == doc_type_filter]
        logger.info("Filtered to %d documents with document_type=%s", len(entries), doc_type_filter)

    doc_count = 0
    total_chunks = 0
    t_start = time.monotonic()

    for entry in entries:
        pdf_path = resolve_corpus_path(entry, CORPUS_DIR)

        if not pdf_path.exists():
            logger.warning("PDF not found, skipping: %s", pdf_path)
            continue

        source_filename = entry.get("source_filename", pdf_path.name)
        logger.info("--- %s ---", source_filename)
        t_doc = time.monotonic()

        def _run_legacy_path(
            manifest_entry: dict[str, object],
            source_pdf_path: Path,
        ) -> tuple[ClassifiedDocument, list[Chunk]]:
            conversion_engine = manifest_entry.get("conversion_engine", "none")

            if conversion_engine != "none":
                converted = convert_pdf(source_pdf_path, MD_CACHE_DIR, engine=conversion_engine)
                age = time.monotonic() - converted.markdown_path.stat().st_mtime
                status = "cached" if age > 1 else "converted"
                logger.info("  convert: %s (%s)", status, conversion_engine)
                extracted_doc = extract_markdown(
                    converted.markdown_path,
                    page_count=converted.page_count,
                )
                extracted_doc.source_path = source_pdf_path
            else:
                extracted_doc = extract_pdf(source_pdf_path)

            logger.info(
                "  extract: %d blocks, %d pages",
                len(extracted_doc.blocks),
                extracted_doc.page_count,
            )

            classified_doc = classify(extracted_doc)
            logger.info(
                "  classify: %s / %s",
                classified_doc.metadata.union_name,
                classified_doc.metadata.document_type,
            )

            legacy_chunks = chunk_document(classified_doc)
            logger.info("  chunk: %d chunks", len(legacy_chunks))
            return classified_doc, legacy_chunks

        def _run_epsca_wage_path(
            source_pdf_path: Path,
        ) -> tuple[ClassifiedDocument, list[Chunk]]:
            pages = parse_wage_schedule_pdf(source_pdf_path)
            page_count = max(page.pdf_page_number for page in pages)
            classified_doc = classify(
                ExtractedDocument(source_path=source_pdf_path, blocks=[], page_count=page_count)
            )
            epsca_chunks = build_wage_chunks(pages, classified_doc.metadata.union_name)
            if not epsca_chunks:
                raise ValueError(f"EPSCA wage parser produced no chunks for {source_pdf_path.name}")
            rate_pages = sum(1 for page in pages if page.groups)
            logger.info(
                "  extract: %d wage pages (%d with rate tables), %d locals",
                len(pages),
                rate_pages,
                len({(page.map_code, page.local, page.city) for page in pages}),
            )
            logger.info(
                "  classify: %s / %s",
                classified_doc.metadata.union_name,
                classified_doc.metadata.document_type,
            )
            logger.info("  chunk: %d chunks (epsca_form)", len(epsca_chunks))
            return classified_doc, epsca_chunks

        classified_and_chunks: tuple[ClassifiedDocument, list[Chunk]] | None = None
        if is_wage_schedule_entry(entry) and epsca_wage_parser_enabled():
            try:
                classified_and_chunks = _run_epsca_wage_path(pdf_path)
            except Exception as exc:  # noqa: BLE001 — any parse failure falls back
                logger.warning("  epsca-form wage parser failed: %s", exc)
                logger.warning("  falling back to legacy extraction path")

        if classified_and_chunks is not None:
            classified, chunks = classified_and_chunks
        else:
            classified, chunks = _run_legacy_path(entry, pdf_path)

        total_chunks += len(chunks)

        # Stage 5: Embed
        embeddings = await embed_chunks(chunks)
        logger.info("  embed: %d vectors", len(embeddings))

        # Stage 6: Store (skipped on --dry-run)
        if dry_run:
            logger.info("  store: SKIPPED (--dry-run)")
        else:
            await store_document(classified, chunks, embeddings)
            logger.info("  store: OK")

        elapsed = time.monotonic() - t_doc
        logger.info("  done in %.1fs", elapsed)
        doc_count += 1

    total_elapsed = time.monotonic() - t_start
    logger.info(
        "Pipeline complete: %d documents, %d chunks, %.1fs total",
        doc_count,
        total_chunks,
        total_elapsed,
    )


# ─── Entry point ──────────────────────────────────────────────────────────────


async def run_stage(stage: str) -> None:
    if stage == "download":
        await _run_download()
    elif stage in ("extract", "classify", "chunk", "embed", "store"):
        logger.error(
            "Stage '%s' cannot be run in isolation — "
            "omit --stage to run the full pipeline, or use --stage download",
            stage,
        )
        raise SystemExit(1)
    else:
        logger.warning("Unknown stage '%s'", stage)


async def main(stages: list[str], dry_run: bool, doc_type_filter: str | None = None) -> None:
    if stages == STAGES:
        # Full pipeline run
        t0 = time.monotonic()
        logger.info("=== Download ===")
        await _run_download()
        logger.info("=== Pipeline (extract → store) ===")
        await _run_full_pipeline(dry_run=dry_run, doc_type_filter=doc_type_filter)
        logger.info("Total wall time: %.1fs", time.monotonic() - t0)
    else:
        # Single-stage run
        for stage in stages:
            logger.info("=== Stage: %s ===", stage)
            await run_stage(stage)
        logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EPSCAxplor ingestion pipeline")
    parser.add_argument(
        "--stage",
        choices=STAGES,
        default=None,
        help="Run a single stage (default: run all stages)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Skip the store stage (embed is still computed but not persisted)",
    )
    parser.add_argument(
        "--doc-type",
        default=os.getenv("INGEST_DOC_TYPE"),
        metavar="DOCUMENT_TYPE",
        help="Process only entries with this document_type (e.g. wage_schedule)",
    )
    args = parser.parse_args()
    selected = [args.stage] if args.stage else STAGES
    asyncio.run(main(selected, dry_run=args.dry_run, doc_type_filter=args.doc_type))
