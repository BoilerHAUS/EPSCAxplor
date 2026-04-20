"""Tests for the Docling + TPDS wage-table ingestion branch."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from wage_tables import (
    WageTableConfig,
    process_wage_schedule_pdf,
    should_use_wage_table_pipeline,
)


_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_FIXTURE_PATH = _FIXTURE_DIR / "epsca_wage_schedule_docling.json"


def _load_docling_fixture() -> dict[str, object]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_should_route_only_when_enabled() -> None:
    entry = {
        "document_type": "wage_schedule",
        "title": "IBEW Generation Wage Schedule E-1-C LU 773 Windsor",
        "source_filename": "E-1-C LU 773 Windsor - May 1, 2025.pdf",
    }

    disabled = WageTableConfig(
        enabled=False,
        fallback_enabled=True,
        artifact_dir=Path("/tmp/ignored"),
        row_group_size=5,
    )
    enabled = WageTableConfig(
        enabled=True,
        fallback_enabled=True,
        artifact_dir=Path("/tmp/ignored"),
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
    assert row_chunk.metadata["wage_schedule"] is True
    assert "Journeyperson" in row_chunk.text
    assert "$44.96" in row_chunk.text

    raw_tables = json.loads(result.artifacts.raw_tables_path.read_text(encoding="utf-8"))
    normalized = json.loads(result.artifacts.normalized_tables_path.read_text(encoding="utf-8"))
    chunk_manifest = json.loads(result.artifacts.chunk_manifest_path.read_text(encoding="utf-8"))

    assert result.artifacts.raw_docling_path.exists()
    assert result.artifacts.raw_tables_path.exists()
    assert result.artifacts.normalized_tables_path.exists()
    assert result.artifacts.chunk_manifest_path.exists()
    assert len(raw_tables) == 1
    assert normalized[0]["tableId"] == "E-1-C LU 773 Windsor - May 1, 2025-table-1"
    assert chunk_manifest[1]["chunkType"] == "row"
