# Runbook: Ingestion Pipeline

## Overview

The ingestion pipeline is a one-time (or periodic) operation — not a persistent service.
It downloads PDFs from epsca.org, extracts text, classifies document type, chunks by
article boundaries, embeds via Ollama, and stores vectors in Qdrant. Wage schedules
can now be routed through an explicit Docling + TPDS branch for row-aware chunks.

## Prerequisites

- `corpus_manifest.yaml` populated with document URLs
- Ollama running with `nomic-embed-text` pulled: `ollama pull nomic-embed-text`
- Qdrant container running and accessible
- `python3 -m pip install -r requirements.txt`
- `npm install` inside `services/ingestion` for the TPDS bridge
- `.env.local` configured with `QDRANT_URL` and `OLLAMA_BASE_URL`

## Run

```bash
cd services/ingestion
python3 -m pip install -r requirements.txt
npm install
python3 run_pipeline.py --dry-run

# Wage schedules only, Docling + TPDS enabled intentionally
INGEST_WAGE_TABLE_PIPELINE=1 python3 run_pipeline.py --doc-type wage_schedule --dry-run
```

## Stages

| Stage | Script | Description |
|---|---|---|
| download | download.py | Fetch PDFs from corpus_manifest.yaml |
| extract | extract.py | Extract text from PDFs with pdfplumber |
| wage-table | wage_tables.py | Optional Docling extraction + TPDS normalization/chunking for wage schedules |
| classify | classify.py | Assign doc_type (primary_ca, nuclear_pa, etc.) |
| chunk | chunk.py | Split by article/section boundaries |
| embed | embed.py | Generate 768-dim vectors via Ollama |
| store | store.py | Upsert vectors into Qdrant |

## Wage-table branch

When `INGEST_WAGE_TABLE_PIPELINE=1` is set, manifest entries already marked as
`document_type: wage_schedule` are routed through:

1. Docling table extraction
2. artifact capture under `services/ingestion/corpus_table_artifacts/<pdf-stem>--<source-hash>/`
   including `manifest.json`, `docling.document.json`, `docling.tables.json`,
   `tpds.tables.json`, and `tpds.chunks.json`
3. TPDS normalization (`normalizeFromDocling`)
4. TPDS chunk generation (`buildTableChunks`)
5. normal embed/store stages using the TPDS-derived chunk text and metadata

The artifact `manifest.json` is the first place to inspect when a wage-table
run looks wrong. It indexes the artifact files and records the source document
id/path, manifest metadata, row-group setting, table counts, and TPDS chunk
counts by type.

If that branch fails and `INGEST_WAGE_TABLE_FALLBACK` is not set to `0`, the
pipeline falls back to the existing Markdown/pdfplumber path.
