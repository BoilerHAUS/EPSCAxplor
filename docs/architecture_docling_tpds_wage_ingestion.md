# Docling + TPDS Wage Ingestion

## Placement

The new wage-schedule branch sits inside `services/ingestion/run_pipeline.py`
before the legacy `convert.py` → `extract.py` → `chunk.py` sequence.

- Non-wage documents: unchanged legacy flow
- Wage schedules with `INGEST_WAGE_TABLE_PIPELINE=1`: `wage_tables.py`
- Wage schedules when the new branch fails and fallback is enabled: unchanged legacy flow

## Flow

1. Route manifest entries with `document_type: wage_schedule` into `wage_tables.py`.
2. Run Docling against the PDF and capture:
   - full Docling document JSON
   - raw Docling table JSON
3. Send each Docling table to the TPDS bridge (`tpds_bridge.mjs`), which calls:
   - `normalizeFromDocling`
   - `buildTableChunks`
4. Persist TPDS normalized tables and chunk manifests as local artifacts.
5. Convert TPDS chunks into the existing ingestion `Chunk` model with extra metadata.
6. Reuse the existing `embed.py` and `store.py` stages unchanged apart from payload enrichment.

## Why This Insertion Point

- It isolates the new behavior to wage schedules.
- It avoids destabilizing clause-oriented chunking for agreements and supplements.
- It preserves the current fallback path for non-table and failure cases.
- It keeps storage and embedding contracts largely stable by adapting TPDS output into the existing `Chunk` shape.

## Artifacts And Metadata

Artifacts are written under `services/ingestion/corpus_table_artifacts/<pdf-stem>/`:

- `docling.document.json`
- `docling.tables.json`
- `tpds.tables.json`
- `tpds.chunks.json`

Stored chunk payloads now carry wage-table-specific metadata such as:

- `table_pipeline`
- `table_chunk_type`
- `table_id`
- `table_title`
- `table_caption`
- `page_numbers`
- `row_indexes`
- `trade_name`
- artifact paths for normalized tables and TPDS chunk output

## First-Pass Limits

- Multi-page logical table merging is not implemented yet.
- Repeated continuation headers depend on Docling output quality and still need real-PDF validation.
- Merged-cell and grouped-header preservation needs broader EPSCA corpus verification, especially for wide schedules.
