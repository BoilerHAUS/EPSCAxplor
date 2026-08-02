# Runbook: Ingestion Pipeline

## Overview

The ingestion pipeline is a one-time (or periodic) operation — not a persistent service.
It downloads PDFs from epsca.org, extracts text, classifies document type, chunks by
article boundaries, embeds via Ollama, and stores vectors in Qdrant.

Wage schedules use a dedicated deterministic parser (`epsca_wage_parser.py`) by
default — see "Wage schedule ingestion" below.

## Prerequisites

- `corpus_manifest.yaml` populated with document URLs
- Ollama running with `nomic-embed-text` pulled: `ollama pull nomic-embed-text`
- Qdrant container running and accessible
- `python3 -m pip install -r requirements.txt`
- `.env.local` configured with `QDRANT_URL` and `OLLAMA_BASE_URL`

## Run

```bash
cd services/ingestion
python3 -m pip install -r requirements.txt
python3 run_pipeline.py --dry-run

# Wage schedules only (EPSCA-form parser is the default path)
python3 run_pipeline.py --doc-type wage_schedule --dry-run
```

## Stages

| Stage | Script | Description |
|---|---|---|
| download | download.py | Fetch PDFs from corpus_manifest.yaml |
| extract | extract.py | Extract text from PDFs with pdfplumber |
| wage parse | epsca_wage_parser.py | Default deterministic parser for wage schedules |
| classify | classify.py | Assign doc_type (primary_ca, nuclear_pa, etc.) |
| chunk | chunk.py | Split by article/section boundaries |
| embed | embed.py | Generate 768-dim vectors via Ollama |
| store | store.py | Delete stale points, then upsert vectors into Qdrant |

## Wage schedule ingestion (default: EPSCA-form parser)

All EPSCA wage schedules share one printed form (MAP CODE header, Local/city block,
classification rows with occupation codes, `YYYY-MM-DD` rate lines). Manifest entries
with `document_type: wage_schedule` are parsed deterministically by
`epsca_wage_parser.py`:

1. Each PDF page is parsed from its text layer (pdfplumber layout mode, with a
   plain-text fallback for oversized page geometries).
2. Column semantics are resolved from the page's printed header keywords
   (pension vs. retirement fund, RRSP variant, Bill 162 / education / provincial
   training tails) and validated with the sum invariant: the component columns
   must sum to TOTAL WAGE PACKAGE. Rows failing the check are flagged
   (`sum_valid: false` in chunk metadata) and logged.
3. One chunk is emitted per classification group. Chunk text is natural language
   and self-contained (union, local, city, schedule code, classification,
   occupation codes, and every effective-dated rate spelled out by column name),
   so both the embedder and the generator can read it. Structured rates are also
   stored in chunk metadata (`classification_names`, `local`, `city`, `rates`,
   `table_pipeline: epsca_form`) — the API's wage retrieval re-rank depends on
   these payload fields.
4. Notes pages (overtime rules, union fund breakdowns) and rate-page footnotes
   become separate narrative chunks, each prefixed with the local's identity.

Disable with `INGEST_EPSCA_WAGE_PARSER=0` (falls back to the legacy
Markdown/pdfplumber path). Any parse failure automatically falls back as well.
(The former Docling + TPDS wage-table branch was retired in #90.)

### Reingesting wage schedules (issues #55 / #59)

After changing the wage parser or chunk format, reingest on the VPS
(see CLAUDE.md "Running ingestion on the VPS" for the socat tunnels):

```bash
POSTGRES_DSN="postgresql://epsca_user:<password>@127.0.0.1:5433/epsca?sslmode=disable" \
  INGEST_DOC_TYPE=wage_schedule \
  python3 run_pipeline.py
```

`store.py` deletes each document's existing Qdrant points before upserting, so a
reingest fully replaces the previous chunks (no stale points when the chunk count
shrinks) — **but only when the `source_filename` is unchanged.** A reissue that
changes the filename inserts a new row/points and orphans the old ones; see
"Applying a corpus-drift update" below. Then rerun the Phase 1 eval
(`services/api/eval/run_eval.py`) and review the wage questions (W01–W12) in
`docs/evaluation/phase1_results.md`.

### Applying a corpus-drift update (issue #178)

The monthly drift check (#91) opens an issue when epsca.org diverges from the
manifest. Resolving it has two traps the plain reingest above does not handle
(orphaned points on a filename change, and re-embedding all ~279 schedules to
fix a handful), so follow this flow.

**1. Update `corpus_manifest.yaml`:**

- **Reissue** (new effective date, e.g. May 2025 → May 2026): update `source_url`,
  `source_filename`, and `effective_date`. The filename **changes**.
- **Rename** (same content, upstream filename normalised): update `source_url`
  only and **keep** `source_filename`, so the existing row updates in place and
  no points orphan.

Confirm the manifest matches the site (exit 0 = clean):

```bash
python3 check_corpus_drift.py
```

**2. Reingest only the changed documents** with `--source-filename` (repeatable)
— not the whole `wage_schedule` set — on the VPS behind the socat tunnels
(see CLAUDE.md "Running ingestion on the VPS"):

```bash
POSTGRES_DSN="postgresql://epsca_user:<password>@127.0.0.1:5433/epsca?sslmode=disable" \
QDRANT_API_KEY="<read-write-key>" \
python3 run_pipeline.py \
  --source-filename "E-10-C LU 353 Oshawa-Port Hope - May 01, 2026.pdf" \
  --source-filename "SM - 14 LU 504 Sudbury - May 1, 2025.pdf"
  # ... one --source-filename per changed doc (new names for reissues,
  #     unchanged names for renames)
```

The download stage fetches only PDFs missing from `corpus/` (reissues have new
names so they download; renames are skipped as already present).

**3. Purge superseded documents — REQUIRED for reissues.** Because a reissue
changes `source_filename`, step 2 created a NEW `documents` row + Qdrant points
and the OLD ones now orphan (their stale rates are still retrievable). Delete
them by their **old** `source_filename` (preview with `--dry-run` first):

```bash
POSTGRES_DSN="postgresql://epsca_user:<password>@127.0.0.1:5433/epsca?sslmode=disable" \
QDRANT_API_KEY="<read-write-key>" \
python3 purge_documents.py --dry-run \
  "E-10-C LU 353 Oshawa-Port Hope - May 1, 2025.pdf"
  # ... one OLD filename per reissue; re-run without --dry-run to delete
```

Renames (step 1, `source_filename` kept) need **no** purge — they update in place.

**4. Verify:** `check_corpus_drift.py` exits 0, and a spot-check query for a
reissued local returns the new effective-dated rate.
