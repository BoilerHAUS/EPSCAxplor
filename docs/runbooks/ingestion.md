# Runbook: Ingestion Pipeline

## Overview

The ingestion pipeline is a one-time (or periodic) operation — not a persistent service.
It downloads PDFs from epsca.org, extracts text, classifies document type, chunks by
article boundaries, embeds via Ollama, and stores vectors in Qdrant.

## Prerequisites

- `corpus_manifest.yaml` populated with document URLs
- Ollama running with `nomic-embed-text` pulled: `ollama pull nomic-embed-text`
- Qdrant container running and accessible
- `.env.local` configured with `QDRANT_URL` and `OLLAMA_URL`

## Run

```bash
cd services/ingestion
pip install -r requirements.txt
python run_pipeline.py --stage all
```

## Stages

| Stage | Script | Description |
|---|---|---|
| download | download.py | Fetch PDFs from corpus_manifest.yaml |
| extract | extract.py | Extract text from PDFs with pdfplumber |
| classify | classify.py | Assign doc_type (primary_ca, nuclear_pa, etc.) |
| chunk | chunk.py | Split by article/section boundaries |
| embed | embed.py | Generate 768-dim vectors via Ollama |
| store | store.py | Upsert vectors into Qdrant |
