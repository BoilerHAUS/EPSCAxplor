"""Tests for the Docling + TPDS wage-table ingestion branch."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from classify import ClassifiedDocument, DocumentMetadata
from extract import ExtractedDocument
from wage_tables import (
    WageTableConfig,
    _prepare_artifact_paths,
    _run_tpds_bridge,
    process_wage_schedule_pdf,
    should_use_wage_table_pipeline,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_FIXTURE_PATH = _FIXTURE_DIR / "epsca_wage_schedule_docling.json"
_MULTI_PAGE_FIXTURE_PATH = _FIXTURE_DIR / "epsca_wage_schedule_docling_multipage.json"
_GROUPED_HEADER_FIXTURE_PATH = _FIXTURE_DIR / "epsca_wage_schedule_docling_grouped_headers.json"


def _load_json_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_docling_fixture() -> dict[str, object]:
    return _load_json_fixture(_FIXTURE_PATH)


def _load_multi_page_docling_fixture() -> dict[str, object]:
    return _load_json_fixture(_MULTI_PAGE_FIXTURE_PATH)


def _load_grouped_header_docling_fixture() -> dict[str, object]:
    return _load_json_fixture(_GROUPED_HEADER_FIXTURE_PATH)


def _classified_wage_doc(pdf_path: Path, title: str) -> ClassifiedDocument:
    return ClassifiedDocument(
        extracted=ExtractedDocument(source_path=pdf_path, blocks=[], page_count=1),
        metadata=DocumentMetadata(
            union_name="IBEW",
            document_type="wage_schedule",
            agreement_scope="generation",
            effective_date="2025-05-01",
            expiry_date=None,
            title=title,
            source_url=None,
        ),
    )


def test_should_route_only_when_enabled() -> None:
    entry = {
        "document_type": "wage_schedule",
        "title": "IBEW Generation Wage Schedule E-1-C LU 773 Windsor",
        "source_filename": "E-1-C LU 773 Windsor - May 1, 2025.pdf",
    }
    ignored_artifact_dir = Path("tests/fixtures/ignored-artifacts")

    disabled = WageTableConfig(
        enabled=False,
        fallback_enabled=True,
        artifact_dir=ignored_artifact_dir,
        row_group_size=5,
    )
    enabled = WageTableConfig(
        enabled=True,
        fallback_enabled=True,
        artifact_dir=ignored_artifact_dir,
        row_group_size=5,
    )

    assert should_use_wage_table_pipeline(entry, disabled) is False
    assert should_use_wage_table_pipeline(entry, enabled) is True


def test_process_wage_schedule_pdf_writes_artifacts_and_tpds_chunks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "E-1-C LU 773 Windsor - May 1, 2025.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf")

    config = WageTableConfig(
        enabled=True,
        fallback_enabled=True,
        artifact_dir=tmp_path / "artifacts",
        row_group_size=3,
    )

    normalized_tables = [
        {
            "tableId": "E-1-C LU 773 Windsor - May 1, 2025-table-1",
            "title": "IBEW Generation Wage Schedule",
            "caption": "IBEW Generation Wage Schedule",
            "pages": [1],
        }
    ]
    table_chunks = [
        {
            "chunkId": "summary-1",
            "tableId": "E-1-C LU 773 Windsor - May 1, 2025-table-1",
            "chunkType": "summary",
            "text": (
                "Table: IBEW Generation Wage Schedule\n"
                "Page Range: 1\n"
                "Classification, Base Rate, Foreperson Differential, Effective Date"
            ),
            "rowIndexes": [],
            "pages": [1],
            "title": "IBEW Generation Wage Schedule",
            "caption": "IBEW Generation Wage Schedule",
            "sectionPath": ["Wage Schedule"]
        },
        {
            "chunkId": "row-1",
            "tableId": "E-1-C LU 773 Windsor - May 1, 2025-table-1",
            "chunkType": "row",
            "text": (
                "Table: IBEW Generation Wage Schedule\n"
                "Page Range: 1\n\n"
                "Row 1\n"
                "Classification: Journeyperson\n"
                "Base Rate: $44.96\n"
                "Foreperson Differential: 12%\n"
                "Effective Date: 2025-05-01"
            ),
            "rowIndexes": [1],
            "pages": [1],
            "title": "IBEW Generation Wage Schedule",
            "caption": "IBEW Generation Wage Schedule",
            "sectionPath": ["Wage Schedule"]
        },
        {
            "chunkId": "row-group-1",
            "tableId": "E-1-C LU 773 Windsor - May 1, 2025-table-1",
            "chunkType": "row-group",
            "text": (
                "Table: IBEW Generation Wage Schedule\n"
                "Page Range: 1\n\n"
                "Row 1\n"
                "Classification: Journeyperson\n"
                "Base Rate: $44.96"
            ),
            "rowIndexes": [1, 2],
            "pages": [1],
            "title": "IBEW Generation Wage Schedule",
            "caption": "IBEW Generation Wage Schedule",
            "sectionPath": ["Wage Schedule"]
        },
    ]

    with (
        patch("wage_tables._extract_docling_document", return_value=_load_docling_fixture()),
        patch("wage_tables._run_tpds_bridge", return_value=(normalized_tables, table_chunks)),
    ):
        result = process_wage_schedule_pdf(pdf_path, config)

    assert result.classified.metadata.document_type == "wage_schedule"
    assert result.classified.metadata.title == "IBEW Generation Wage Schedule E-1-C LU 773 Windsor"
    assert result.page_count == 1
    assert result.table_count == 1
    assert len(result.chunks) == 3

    row_chunk = result.chunks[1]
    assert row_chunk.is_table is True
    assert row_chunk.article_title == "IBEW Generation Wage Schedule"
    assert row_chunk.metadata is not None
    assert row_chunk.metadata["table_pipeline"] == "docling_tpds"
    assert row_chunk.metadata["table_chunk_type"] == "row"
    assert row_chunk.metadata["table_id"] == "E-1-C LU 773 Windsor - May 1, 2025-table-1"
    assert row_chunk.metadata["row_indexes"] == [1]
    assert row_chunk.metadata["page_numbers"] == [1]
    assert row_chunk.metadata["trade_name"] == "IBEW Generation"
    assert row_chunk.metadata["source_document_path"] == str(pdf_path)
    assert row_chunk.metadata["source_document_filename"] == pdf_path.name
    assert row_chunk.metadata["wage_schedule"] is True
    assert "Journeyperson" in row_chunk.text
    assert "$44.96" in row_chunk.text

    manifest = json.loads(result.artifacts.manifest_path.read_text(encoding="utf-8"))
    raw_tables = json.loads(result.artifacts.raw_tables_path.read_text(encoding="utf-8"))
    normalized = json.loads(result.artifacts.normalized_tables_path.read_text(encoding="utf-8"))
    chunk_manifest = json.loads(result.artifacts.chunk_manifest_path.read_text(encoding="utf-8"))

    assert result.artifacts.artifact_dir.name.startswith(
        "E-1-C LU 773 Windsor - May 1, 2025--"
    )
    assert result.artifacts.manifest_path.exists()
    assert result.artifacts.raw_docling_path.exists()
    assert result.artifacts.raw_tables_path.exists()
    assert result.artifacts.normalized_tables_path.exists()
    assert result.artifacts.chunk_manifest_path.exists()
    assert manifest["schema_version"] == 1
    assert manifest["pipeline"] == "docling_tpds"
    assert manifest["source_document"]["path"] == str(pdf_path)
    assert manifest["source_document"]["filename"] == pdf_path.name
    assert manifest["source_document"]["title"] == result.classified.metadata.title
    assert manifest["source_document"]["trade_name"] == "IBEW Generation"
    assert manifest["counts"]["page_count"] == 1
    assert manifest["counts"]["docling_table_count"] == 1
    assert manifest["counts"]["tpds_table_count"] == 1
    assert manifest["counts"]["tpds_chunk_count"] == 3
    assert manifest["counts"]["chunk_types"] == {"summary": 1, "row": 1, "row-group": 1}
    assert manifest["artifacts"]["manifest_path"] == str(result.artifacts.manifest_path)
    assert manifest["tables"] == [
        {
            "table_id": "E-1-C LU 773 Windsor - May 1, 2025-table-1",
            "title": "IBEW Generation Wage Schedule",
            "caption": "IBEW Generation Wage Schedule",
            "pages": [1],
            "chunk_count": 3,
            "chunk_types": {"summary": 1, "row": 1, "row-group": 1},
        }
    ]
    assert len(raw_tables) == 1
    assert normalized[0]["tableId"] == "E-1-C LU 773 Windsor - May 1, 2025-table-1"
    assert chunk_manifest[1]["chunkType"] == "row"


def test_prepare_artifact_paths_namespaces_same_filename_paths(tmp_path: Path) -> None:
    config = WageTableConfig(
        enabled=True,
        fallback_enabled=True,
        artifact_dir=tmp_path / "artifacts",
        row_group_size=3,
    )

    first_pdf = tmp_path / "set-a" / "wage.pdf"
    second_pdf = tmp_path / "set-b" / "wage.pdf"

    first_artifacts = _prepare_artifact_paths(first_pdf, config)
    second_artifacts = _prepare_artifact_paths(second_pdf, config)

    assert first_artifacts.artifact_dir != second_artifacts.artifact_dir
    assert first_artifacts.artifact_dir.name.startswith("wage--")
    assert second_artifacts.artifact_dir.name.startswith("wage--")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js required for TPDS bridge")
def test_process_wage_schedule_pdf_merges_multi_page_tables_and_suppresses_repeated_headers(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "E-1-C LU 773 Windsor - May 1, 2025.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf")

    config = WageTableConfig(
        enabled=True,
        fallback_enabled=True,
        artifact_dir=tmp_path / "artifacts",
        row_group_size=2,
    )

    with patch(
        "wage_tables._extract_docling_document",
        return_value=_load_multi_page_docling_fixture(),
    ):
        result = process_wage_schedule_pdf(pdf_path, config)

    assert result.page_count == 2
    assert result.table_count == 2
    assert len(result.chunks) == 7

    row_chunks = [
        chunk for chunk in result.chunks if chunk.metadata["table_chunk_type"] == "row"
    ]
    row_group_chunks = [
        chunk for chunk in result.chunks if chunk.metadata["table_chunk_type"] == "row-group"
    ]

    assert len(row_chunks) == 4
    assert len(row_group_chunks) == 2
    assert all("Classification: Classification" not in chunk.text for chunk in result.chunks)
    assert all("Base Rate: Base Rate" not in chunk.text for chunk in result.chunks)
    assert any("Apprentice 1st Term" in chunk.text for chunk in row_chunks)
    assert any("General Foreperson" in chunk.text for chunk in row_chunks)

    normalized = json.loads(result.artifacts.normalized_tables_path.read_text(encoding="utf-8"))
    manifest = json.loads(result.artifacts.manifest_path.read_text(encoding="utf-8"))

    assert len(normalized) == 1
    assert normalized[0]["pages"] == [1, 2]
    assert normalized[0]["continuity"]["isMultiPage"] is True
    assert "multi-page-merged" in normalized[0]["fidelityWarnings"]
    repeated_rows = [row for row in normalized[0]["rows"] if row.get("repeatedHeaderRow")]
    assert len(repeated_rows) == 1
    assert repeated_rows[0]["page"] == 2

    assert manifest["counts"]["docling_table_count"] == 2
    assert manifest["counts"]["tpds_table_count"] == 1
    assert manifest["counts"]["tpds_chunk_count"] == 7
    assert manifest["counts"]["chunk_types"] == {"summary": 1, "row": 4, "row-group": 2}
    assert manifest["tables"] == [
        {
            "table_id": "E-1-C LU 773 Windsor - May 1, 2025-table-1",
            "title": "IBEW Generation Wage Schedule",
            "caption": "IBEW Generation Wage Schedule",
            "pages": [1, 2],
            "chunk_count": 7,
            "chunk_types": {"summary": 1, "row": 4, "row-group": 2},
        }
    ]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js required for TPDS bridge")
def test_run_tpds_bridge_preserves_grouped_headers_and_merged_cells(tmp_path: Path) -> None:
    pdf_path = tmp_path / "E-1-C LU 773 Windsor - May 1, 2025.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf")

    config = WageTableConfig(
        enabled=True,
        fallback_enabled=True,
        artifact_dir=tmp_path / "artifacts",
        row_group_size=2,
    )

    raw_tables = _load_grouped_header_docling_fixture()["tables"]
    assert isinstance(raw_tables, list)

    normalized_tables, table_chunks = _run_tpds_bridge(
        raw_tables,
        _classified_wage_doc(pdf_path, "IBEW Generation Wage Schedule E-1-C LU 773 Windsor"),
        pdf_path,
        config,
    )

    assert len(normalized_tables) == 1
    assert len(table_chunks) == 4

    normalized_table = normalized_tables[0]
    merged_header = next(
        cell for cell in normalized_table["cells"] if cell["textNormalized"] == "Base Rates"
    )
    stacked_header = next(
        cell for cell in normalized_table["cells"] if cell["textNormalized"] == "Classification"
    )

    assert merged_header["colSpan"] == 2
    assert stacked_header["rowSpan"] == 2

    row_chunks = [chunk for chunk in table_chunks if chunk["chunkType"] == "row"]
    assert len(row_chunks) == 2
    assert "Base Rates > Day Shift: $44.96" in row_chunks[0]["text"]
    assert "Base Rates > Night Shift: $46.96" in row_chunks[0]["text"]
    assert "Effective Date: 2025-05-01" in row_chunks[0]["text"]
