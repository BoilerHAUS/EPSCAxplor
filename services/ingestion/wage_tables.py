"""Docling + TPDS helpers for wage-schedule ingestion."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from chunk import Chunk
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from classify import ClassifiedDocument, classify
from extract import ExtractedDocument

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
_DEFAULT_ARTIFACT_DIR = _HERE / "corpus_table_artifacts"
_TPDS_BRIDGE_PATH = _HERE / "tpds_bridge.mjs"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class WageTableConfig:
    enabled: bool
    fallback_enabled: bool
    artifact_dir: Path
    row_group_size: int

    @classmethod
    def from_env(cls) -> WageTableConfig:
        artifact_root = Path(
            os.getenv("INGEST_WAGE_TABLE_ARTIFACT_DIR", str(_DEFAULT_ARTIFACT_DIR))
        )
        row_group_size = int(os.getenv("INGEST_WAGE_TABLE_ROW_GROUP_SIZE", "5"))
        return cls(
            enabled=_env_bool("INGEST_WAGE_TABLE_PIPELINE", False),
            fallback_enabled=_env_bool("INGEST_WAGE_TABLE_FALLBACK", True),
            artifact_dir=artifact_root,
            row_group_size=max(1, row_group_size),
        )


@dataclass(frozen=True)
class WageTableArtifacts:
    artifact_dir: Path
    raw_docling_path: Path
    raw_tables_path: Path
    normalized_tables_path: Path
    chunk_manifest_path: Path


@dataclass(frozen=True)
class WageTableProcessingResult:
    classified: ClassifiedDocument
    chunks: list[Chunk]
    page_count: int
    table_count: int
    artifacts: WageTableArtifacts


def should_use_wage_table_pipeline(
    entry: dict[str, Any],
    config: WageTableConfig,
) -> bool:
    """Route manifest-marked wage schedules into the Docling + TPDS branch."""
    if not config.enabled:
        return False

    document_type = str(entry.get("document_type", "")).strip().lower()
    if document_type == "wage_schedule":
        return True

    title = str(entry.get("title", "")).lower()
    source_filename = str(entry.get("source_filename", "")).lower()
    return "wage schedule" in title or "wage schedule" in source_filename


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _page_count_from_docling_export(docling_export: dict[str, Any]) -> int:
    pages = docling_export.get("pages", {})
    if isinstance(pages, dict):
        return len(pages)
    if isinstance(pages, list):
        return len(pages)
    return 0


def _extract_docling_document(pdf_path: Path) -> dict[str, Any]:
    from docling.document_converter import DocumentConverter  # type: ignore[import]

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    exported = result.document.export_to_dict()
    if not isinstance(exported, dict):
        raise TypeError("Docling export_to_dict() did not return a JSON object.")
    return exported


def _prepare_artifact_paths(pdf_path: Path, config: WageTableConfig) -> WageTableArtifacts:
    artifact_dir = config.artifact_dir / pdf_path.stem
    return WageTableArtifacts(
        artifact_dir=artifact_dir,
        raw_docling_path=artifact_dir / "docling.document.json",
        raw_tables_path=artifact_dir / "docling.tables.json",
        normalized_tables_path=artifact_dir / "tpds.tables.json",
        chunk_manifest_path=artifact_dir / "tpds.chunks.json",
    )


def _table_title(raw_table: dict[str, Any], doc_title: str, index: int) -> str:
    caption = raw_table.get("caption")
    if isinstance(caption, str) and caption.strip():
        return caption.strip()
    return f"{doc_title} — Table {index + 1}"


def _run_tpds_bridge(
    raw_tables: list[dict[str, Any]],
    doc: ClassifiedDocument,
    pdf_path: Path,
    config: WageTableConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    node_executable = shutil.which("node")
    if not node_executable:
        raise RuntimeError(
            "Node.js is required for the TPDS bridge. Install Node 18+ and run npm install "
            "in services/ingestion."
        )

    bridge_payload = {
        "tables": [
            {
                "tableItem": table_item,
                "options": {
                    "tableId": f"{pdf_path.stem}-table-{index + 1}",
                    "title": _table_title(table_item, doc.metadata.title, index),
                    "caption": table_item.get("caption"),
                    "sourceDocumentId": str(pdf_path),
                },
            }
            for index, table_item in enumerate(raw_tables)
        ],
        "chunkOptions": {
            "rowGroupSize": config.row_group_size,
            "includeSummaryChunk": True,
            "includeRowChunks": True,
            "includeRowGroupChunks": True,
            "includeNotesChunk": True,
        },
    }

    try:
        completed = subprocess.run(  # noqa: S603
            [node_executable, str(_TPDS_BRIDGE_PATH)],
            cwd=_HERE,
            input=json.dumps(bridge_payload),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Node.js is required for the TPDS bridge. Install Node 18+ and run npm install "
            "in services/ingestion."
        ) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(f"TPDS bridge failed: {detail}")

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TPDS bridge returned invalid JSON.") from exc

    normalized_tables = payload.get("normalizedTables")
    table_chunks = payload.get("tableChunks")
    if not isinstance(normalized_tables, list) or not isinstance(table_chunks, list):
        raise RuntimeError("TPDS bridge output is missing normalized tables or chunks.")

    return normalized_tables, table_chunks


def _derive_trade_name(doc: ClassifiedDocument) -> str:
    title = doc.metadata.title
    if " Wage Schedule " in title:
        return title.split(" Wage Schedule ", maxsplit=1)[0].strip()
    return doc.metadata.union_name


def _tpds_chunks_to_ingestion_chunks(
    doc: ClassifiedDocument,
    pdf_path: Path,
    artifacts: WageTableArtifacts,
    tpds_chunks: list[dict[str, Any]],
) -> list[Chunk]:
    trade_name = _derive_trade_name(doc)
    chunks: list[Chunk] = []

    for index, table_chunk in enumerate(tpds_chunks):
        if not isinstance(table_chunk, dict):
            continue

        page_numbers = table_chunk.get("pages")
        normalized_pages = (
            [int(page) for page in page_numbers if isinstance(page, int)]
            if isinstance(page_numbers, list)
            else []
        )
        page_number = normalized_pages[0] if normalized_pages else 1

        row_indexes = table_chunk.get("rowIndexes")
        normalized_rows = (
            [int(row) for row in row_indexes if isinstance(row, int)]
            if isinstance(row_indexes, list)
            else []
        )

        section_path = table_chunk.get("sectionPath")
        normalized_section_path = (
            [str(part) for part in section_path]
            if isinstance(section_path, list)
            else None
        )

        table_title = table_chunk.get("title")
        title_text = str(table_title) if isinstance(table_title, str) else None
        caption = table_chunk.get("caption")
        caption_text = str(caption) if isinstance(caption, str) else None

        metadata: dict[str, object] = {
            "document_title": doc.metadata.title,
            "trade_name": trade_name,
            "table_pipeline": "docling_tpds",
            "table_chunk_type": str(table_chunk.get("chunkType", "")),
            "table_id": str(table_chunk.get("tableId", "")),
            "table_title": title_text or doc.metadata.title,
            "table_caption": caption_text,
            "page_numbers": normalized_pages,
            "row_indexes": normalized_rows,
            "section_path": normalized_section_path,
            "source_document_path": str(pdf_path),
            "raw_docling_tables_path": str(artifacts.raw_tables_path),
            "normalized_table_json_path": str(artifacts.normalized_tables_path),
            "tpds_chunk_manifest_path": str(artifacts.chunk_manifest_path),
            "wage_schedule": True,
        }

        chunks.append(
            Chunk(
                text=str(table_chunk.get("text", "")),
                page_number=page_number,
                is_table=True,
                article_number=None,
                section_number=None,
                article_title=title_text or caption_text or doc.metadata.title,
                chunk_index=index,
                metadata=metadata,
            )
        )

    return chunks


def process_wage_schedule_pdf(
    pdf_path: Path,
    config: WageTableConfig,
) -> WageTableProcessingResult:
    """Extract, normalize, chunk, and artifact a wage schedule PDF."""
    artifacts = _prepare_artifact_paths(pdf_path, config)
    docling_export = _extract_docling_document(pdf_path)
    raw_tables = docling_export.get("tables", [])

    if not isinstance(raw_tables, list) or not raw_tables:
        raise ValueError(f"Docling found no tables in wage schedule PDF: {pdf_path.name}")

    page_count = _page_count_from_docling_export(docling_export)
    classified = classify(
        ExtractedDocument(
            source_path=pdf_path,
            blocks=[],
            page_count=page_count,
        )
    )

    normalized_tables, table_chunks = _run_tpds_bridge(raw_tables, classified, pdf_path, config)

    _write_json(artifacts.raw_docling_path, docling_export)
    _write_json(artifacts.raw_tables_path, raw_tables)
    _write_json(artifacts.normalized_tables_path, normalized_tables)
    _write_json(artifacts.chunk_manifest_path, table_chunks)

    chunks = _tpds_chunks_to_ingestion_chunks(classified, pdf_path, artifacts, table_chunks)
    logger.info(
        "  wage-table: Docling tables=%d, TPDS chunks=%d, artifacts=%s",
        len(raw_tables),
        len(chunks),
        artifacts.artifact_dir,
    )

    return WageTableProcessingResult(
        classified=classified,
        chunks=chunks,
        page_count=page_count,
        table_count=len(raw_tables),
        artifacts=artifacts,
    )
