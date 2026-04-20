"""Docling + TPDS helpers for wage-schedule ingestion."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import uuid
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
    manifest_path: Path
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


def _source_document_key(pdf_path: Path) -> str:
    try:
        return str(pdf_path.resolve().relative_to(_HERE.resolve()))
    except ValueError:
        return str(pdf_path.resolve())


def _source_document_id(pdf_path: Path) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, _source_document_key(pdf_path)))


def _artifact_dir_name(pdf_path: Path) -> str:
    source_digest = _source_document_id(pdf_path).replace("-", "")[:12]
    return f"{pdf_path.stem}--{source_digest}"


def _prepare_artifact_paths(pdf_path: Path, config: WageTableConfig) -> WageTableArtifacts:
    artifact_dir = config.artifact_dir / _artifact_dir_name(pdf_path)
    return WageTableArtifacts(
        artifact_dir=artifact_dir,
        manifest_path=artifact_dir / "manifest.json",
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
                    "sourceDocumentId": _source_document_id(pdf_path),
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


def _normalize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []

    normalized: list[int] = []
    for item in value:
        if isinstance(item, int) and item not in normalized:
            normalized.append(item)
    return normalized


def _normalize_str_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None

    normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return normalized or None


def _chunk_type_counts(chunks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        chunk_type = _normalize_text(chunk.get("chunkType")) or "unknown"
        counts[chunk_type] = counts.get(chunk_type, 0) + 1
    return counts


def _table_manifest_entries(
    normalized_tables: list[dict[str, Any]],
    table_chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chunk_counts_by_table: dict[str, dict[str, int]] = {}
    for table_chunk in table_chunks:
        if not isinstance(table_chunk, dict):
            continue

        table_id = _normalize_text(table_chunk.get("tableId"))
        if not table_id:
            continue

        table_counts = chunk_counts_by_table.setdefault(table_id, {})
        chunk_type = _normalize_text(table_chunk.get("chunkType")) or "unknown"
        table_counts[chunk_type] = table_counts.get(chunk_type, 0) + 1

    table_entries: list[dict[str, Any]] = []
    for index, normalized_table in enumerate(normalized_tables):
        if not isinstance(normalized_table, dict):
            continue

        table_id = _normalize_text(normalized_table.get("tableId")) or f"table-{index + 1}"
        table_chunk_counts = chunk_counts_by_table.get(table_id, {})
        table_entries.append(
            {
                "table_id": table_id,
                "title": _normalize_text(normalized_table.get("title")),
                "caption": _normalize_text(normalized_table.get("caption")),
                "pages": _normalize_int_list(normalized_table.get("pages")),
                "chunk_count": sum(table_chunk_counts.values()),
                "chunk_types": table_chunk_counts,
            }
        )

    return table_entries


def _build_artifact_manifest(
    doc: ClassifiedDocument,
    pdf_path: Path,
    config: WageTableConfig,
    artifacts: WageTableArtifacts,
    page_count: int,
    raw_tables: list[dict[str, Any]],
    normalized_tables: list[dict[str, Any]],
    table_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pipeline": "docling_tpds",
        "source_document": {
            "id": _source_document_id(pdf_path),
            "key": _source_document_key(pdf_path),
            "path": str(pdf_path),
            "filename": pdf_path.name,
            "title": doc.metadata.title,
            "union_name": doc.metadata.union_name,
            "trade_name": _derive_trade_name(doc),
            "document_type": doc.metadata.document_type,
            "agreement_scope": doc.metadata.agreement_scope,
            "effective_date": doc.metadata.effective_date,
            "expiry_date": doc.metadata.expiry_date,
            "source_url": doc.metadata.source_url,
        },
        "settings": {
            "row_group_size": config.row_group_size,
        },
        "counts": {
            "page_count": page_count,
            "docling_table_count": len(raw_tables),
            "tpds_table_count": len(normalized_tables),
            "tpds_chunk_count": len(table_chunks),
            "chunk_types": _chunk_type_counts(table_chunks),
        },
        "artifacts": {
            "artifact_dir": str(artifacts.artifact_dir),
            "manifest_path": str(artifacts.manifest_path),
            "raw_docling_path": str(artifacts.raw_docling_path),
            "raw_tables_path": str(artifacts.raw_tables_path),
            "normalized_tables_path": str(artifacts.normalized_tables_path),
            "chunk_manifest_path": str(artifacts.chunk_manifest_path),
        },
        "tables": _table_manifest_entries(normalized_tables, table_chunks),
    }


def _tpds_chunks_to_ingestion_chunks(
    doc: ClassifiedDocument,
    pdf_path: Path,
    artifacts: WageTableArtifacts,
    tpds_chunks: list[dict[str, Any]],
) -> list[Chunk]:
    trade_name = _derive_trade_name(doc)
    source_document_id = _source_document_id(pdf_path)
    chunks: list[Chunk] = []

    for index, table_chunk in enumerate(tpds_chunks):
        if not isinstance(table_chunk, dict):
            continue

        normalized_pages = _normalize_int_list(table_chunk.get("pages"))
        page_number = normalized_pages[0] if normalized_pages else 1

        normalized_rows = _normalize_int_list(table_chunk.get("rowIndexes"))
        normalized_section_path = _normalize_str_list(table_chunk.get("sectionPath"))

        title_text = _normalize_text(table_chunk.get("title"))
        caption_text = _normalize_text(table_chunk.get("caption"))
        table_id = _normalize_text(table_chunk.get("tableId"))
        chunk_type = _normalize_text(table_chunk.get("chunkType"))

        metadata: dict[str, object] = {
            "document_title": doc.metadata.title,
            "trade_name": trade_name,
            "table_pipeline": "docling_tpds",
            "table_chunk_type": chunk_type,
            "table_id": table_id,
            "table_title": title_text or doc.metadata.title,
            "table_caption": caption_text,
            "page_numbers": normalized_pages,
            "row_indexes": normalized_rows,
            "section_path": normalized_section_path,
            "source_document_id": source_document_id,
            "source_document_path": str(pdf_path),
            "source_document_filename": pdf_path.name,
            "artifact_manifest_path": str(artifacts.manifest_path),
            "table_artifact_dir": str(artifacts.artifact_dir),
            "raw_docling_document_path": str(artifacts.raw_docling_path),
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
    artifact_manifest = _build_artifact_manifest(
        classified,
        pdf_path,
        config,
        artifacts,
        page_count,
        raw_tables,
        normalized_tables,
        table_chunks,
    )

    _write_json(artifacts.raw_docling_path, docling_export)
    _write_json(artifacts.raw_tables_path, raw_tables)
    _write_json(artifacts.normalized_tables_path, normalized_tables)
    _write_json(artifacts.chunk_manifest_path, table_chunks)
    _write_json(artifacts.manifest_path, artifact_manifest)

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
