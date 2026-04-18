<div align="center">
  <h1>EPSCAxplor</h1>
  <p><strong>Grounded answers for EPSCA collective agreements, nuclear project agreements, and wage schedules.</strong></p>
  <p>
    A retrieval-augmented reference system for Ontario construction labour documents.
    It ingests agreement PDFs, preserves clause and table structure, retrieves relevant chunks,
    and generates cited answers with an explicit legal disclaimer.
  </p>

  <p>
    <a href="#quickstart"><strong>Quickstart</strong></a>
    •
    <a href="#architecture"><strong>Architecture</strong></a>
    •
    <a href="#query-api"><strong>Query API</strong></a>
    •
    <a href="#ingestion-pipeline"><strong>Ingestion Pipeline</strong></a>
    •
    <a href="#project-state"><strong>Project State</strong></a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/status-phase%201%20POC-0f766e?style=for-the-badge" alt="Phase 1 POC badge" />
    <img src="https://img.shields.io/badge/backend-FastAPI-059669?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI badge" />
    <img src="https://img.shields.io/badge/frontend-Next.js%2015-111111?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js badge" />
    <img src="https://img.shields.io/badge/vector-Qdrant-e11d48?style=for-the-badge" alt="Qdrant badge" />
    <img src="https://img.shields.io/badge/embeddings-Ollama%20%2B%20nomic-2563eb?style=for-the-badge" alt="Ollama badge" />
    <img src="https://img.shields.io/badge/generation-Claude%20Haiku%20%2F%20Sonnet-f59e0b?style=for-the-badge" alt="Claude badge" />
  </p>
</div>

> Built for the kind of field question where a wrong answer can turn into a grievance, a delay, or a very expensive argument.

---

## Table of Contents

- [Why EPSCAxplor exists](#why-epscaxplor-exists)
- [What the system does today](#what-the-system-does-today)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Query API](#query-api)
- [Ingestion pipeline](#ingestion-pipeline)
- [Corpus snapshot](#corpus-snapshot)
- [Repository layout](#repository-layout)
- [Project state](#project-state)
- [Documentation](#documentation)
- [License](#license)

## Why EPSCAxplor exists

EPSCA job sites routinely involve multiple unions, multiple agreement types, and questions that need fast answers:

- What counts as overtime for a given trade?
- Does nuclear project work change the governing clause?
- Which wage schedule applies to a specific local and effective date?
- Is a provision in the primary collective agreement overridden somewhere else?

Manual lookup is slow. Cross-document comparison is worse. Wage schedules are especially painful because the critical information often lives inside table-heavy PDFs.

EPSCAxplor is designed to make those answers:

- **Grounded** in retrieved source text only
- **Cited** back to a specific source block
- **Version-aware** through document metadata and effective dates
- **Explicitly disclaimed** as reference material, not legal advice

## What the system does today

| Capability | Current implementation |
| --- | --- |
| API | FastAPI service with `/health` and `/query` |
| Retrieval | Qdrant similarity search with union, nuclear, scope, and date filters |
| Generation | Claude Haiku for standard questions, Claude Sonnet for cross-union comparisons |
| Embeddings | Ollama with `nomic-embed-text` |
| Corpus ingestion | Download, PDF extraction, optional PDF-to-Markdown conversion, classification, chunking, embedding, storage |
| Data model | PostgreSQL for documents, tenants, users, subscriptions, API keys, and query logs |
| Frontend | Next.js app scaffold; current UI is still a placeholder |
| Evaluation | 30-question Phase 1 POC evaluator targeting live API responses |

### Highlights

- **Structure-aware chunking** splits agreement text at article and section boundaries instead of blunt fixed windows.
- **Table-preserving conversion** uses `pymupdf4llm` for wage schedule PDFs so rows survive ingestion.
- **Nuclear-aware retrieval** widens the search space when the query references OPG, Bruce Power, Darlington, Pickering, or other nuclear context.
- **Scope-aware retrieval** supports generation vs. transmission filtering where agreements differ.
- **Best-effort audit logging** writes query logs without blocking answer delivery.

## Architecture

```mermaid
flowchart LR
    U[User / Chat UI] --> W[Next.js Web]
    W --> A[FastAPI API]
    A --> P[Preprocess Query]
    P --> R[Qdrant Retrieval]
    R --> C[Assemble Context]
    C --> G[Claude Generation]
    G --> X[Citation Extraction]
    X --> L[Query Logging in PostgreSQL]
    X --> O[Structured Answer]

    I[Ingestion Pipeline] --> PG[(PostgreSQL)]
    I --> Q[(Qdrant)]
    R --> Q
    L --> PG
    C --> PG
```

### Query flow

```mermaid
flowchart TD
    Q1[Raw user question] --> Q2[Detect union, nuclear context, scope, complexity]
    Q2 --> Q3[Embed query with Ollama]
    Q3 --> Q4[Filtered top-k retrieval from Qdrant]
    Q4 --> Q5[Hydrate titles from PostgreSQL]
    Q5 --> Q6[Build numbered SOURCE blocks]
    Q6 --> Q7[Generate answer with Claude]
    Q7 --> Q8[Extract citation refs]
    Q8 --> Q9[Return answer, citations, model_used, disclaimer, query_log_id]
```

### Ingestion flow

```mermaid
flowchart LR
    D[download.py] --> E[extract.py]
    E --> K[classify.py]
    K --> C[chunk.py]
    C --> M[embed.py]
    M --> S[store.py]
    S --> Q[(Qdrant)]
    S --> P[(PostgreSQL)]
    V[convert.py] --> E
```

## Quickstart

The most reliable local workflow right now is:

1. Run infrastructure in Docker.
2. Apply the SQL migrations.
3. Run the API and web app directly from the host.
4. Run ingestion as a one-shot script when you need to rebuild corpus state.

### 1. Configure environment

Create a root `.env` from the example:

```bash
cp .env.example .env
```

For host-based local development, these are the values that matter most:

```env
DATABASE_URL=postgresql://epsca_user:replace-with-strong-password@localhost:5432/epsca
QDRANT_URL=http://localhost:6333
OLLAMA_URL=http://localhost:11434
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Start PostgreSQL and Qdrant

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.dev.yml \
  up -d epsca-db epsca-qdrant
```

### 3. Apply database migrations

Run the SQL files in order against your local database:

```bash
export DATABASE_URL_LOCAL="postgresql://epsca_user:replace-with-strong-password@localhost:5432/epsca"

for file in infra/db/migrations/*.sql; do
  psql "$DATABASE_URL_LOCAL" -f "$file"
done
```

### 4. Make sure Ollama has the embedding model

```bash
ollama pull nomic-embed-text
```

### 5. Run the API

```bash
cd services/api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://epsca_user:replace-with-strong-password@localhost:5432/epsca"
export QDRANT_URL="http://localhost:6333"
export OLLAMA_URL="http://localhost:11434"
export ANTHROPIC_API_KEY="your-key"
export JWT_SECRET="replace-with-random-hex-string"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run the web app

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

### 7. Run ingestion

The ingestion scripts use slightly different env var names than the API:

- API uses `DATABASE_URL` and `OLLAMA_URL`
- Ingestion uses `POSTGRES_DSN` and `OLLAMA_BASE_URL`

```bash
cd services/ingestion
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export POSTGRES_DSN="postgresql://epsca_user:replace-with-strong-password@localhost:5432/epsca"
export QDRANT_URL="http://localhost:6333"
export OLLAMA_BASE_URL="http://localhost:11434"
python run_pipeline.py
```

### 8. Run the test suites

API:

```bash
cd services/api
. .venv/bin/activate
pytest
```

Ingestion:

```bash
cd services/ingestion
. .venv/bin/activate
pytest
```

## Query API

### Health check

```bash
curl http://localhost:8000/health
```

Expected shape:

```json
{
  "status": "ok",
  "dependencies": {
    "database": "ok",
    "qdrant": "ok",
    "ollama": "ok"
  }
}
```

### Query request

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare the overtime rules for IBEW Generation and Sheet Metal workers."
  }'
```

Response shape:

```json
{
  "answer": "...",
  "citations": [
    {
      "source_number": 1,
      "union_name": "IBEW",
      "document_title": "IBEW Generation 2025-2030 Collective Agreement",
      "document_type": "primary_ca",
      "effective_date": "2025-05-01",
      "article": "Article 12",
      "section": "12.03",
      "article_title": "Overtime",
      "page_number": 34,
      "excerpt": "..."
    }
  ],
  "model_used": "claude-sonnet-4-6",
  "disclaimer": "This answer is for reference only and does not constitute legal advice. Consult qualified labour relations counsel for binding interpretations.",
  "query_log_id": "..."
}
```

## Ingestion pipeline

The ingestion service is not a long-running app. It is a staged pipeline:

| Stage | Purpose |
| --- | --- |
| `download.py` | Fetch PDFs from the manifest and store them under `corpus/` |
| `convert.py` | Convert table-heavy PDFs to Markdown when configured |
| `extract.py` | Extract text blocks and table blocks with page numbers |
| `classify.py` | Attach manifest metadata to the extracted document |
| `chunk.py` | Split content by structure, preserving article and section metadata |
| `embed.py` | Generate 768-dim vectors via Ollama |
| `store.py` | Upsert document records into PostgreSQL and chunk points into Qdrant |

Useful commands:

```bash
# Download only
python run_pipeline.py --stage download

# Full run without writing to storage
python run_pipeline.py --dry-run

# Full run for one document type
python run_pipeline.py --doc-type wage_schedule
```

## Corpus snapshot

The repository is currently in a **Phase 1 POC** state.

| Snapshot | Value |
| --- | --- |
| Current manifest entries | 51 documents |
| Unions currently represented in the checked-in manifest | 3 |
| Document types currently represented | Primary CAs, Nuclear Project Agreements, Wage Schedules |
| Full project target from planning docs | ~58 documents across 18 unions |
| Evaluation harness | 30 gold questions in `services/api/eval/run_eval.py` |

Table-heavy wage schedules are a first-class retrieval problem in this repo, which is why the pipeline now supports PDF-to-Markdown conversion before chunking:

<p align="center">
  <img src="docs/evaluation/image.png" alt="Excerpt from an EPSCA wage schedule PDF showing dense tabular rate data" width="760" />
</p>

To run the Phase 1 evaluator against a live API:

```bash
python services/api/eval/run_eval.py
```

Generated output is written to [`docs/evaluation/phase1_results.md`](docs/evaluation/phase1_results.md).

## Repository layout

```text
EPSCAxplor/
├── apps/
│   └── web/                   # Next.js frontend
├── services/
│   ├── api/                   # FastAPI query service
│   └── ingestion/             # One-shot ingestion pipeline
├── infra/
│   ├── db/migrations/         # PostgreSQL schema
│   └── docker/                # Compose files for local/dev/prod-style stacks
├── docs/
│   ├── architecture.md
│   ├── planning.md
│   ├── github-workflow.md
│   ├── issues.md
│   ├── evaluation/
│   └── runbooks/
├── CHANGELOG.md
├── CLAUDE.md
└── .env.example
```

## Project state

EPSCAxplor already has the core RAG spine in place, but it is not pretending to be further along than it is.

### What is built

- FastAPI query endpoint with preprocessing, retrieval, generation, citation extraction, and query logging
- Postgres and Qdrant persistence layers
- Ingestion pipeline with conversion support for wage schedule PDFs
- Tests across API and ingestion modules
- Deployment and operational runbooks

### What is still incomplete

- The Next.js frontend is still a scaffold
- Auth is currently a Phase 1 stub, not enforced JWT auth
- Manual review of evaluation correctness and citation validity is still pending

### Known gaps already tracked in the repo

- Wage schedule rate rows are not consistently retrieved yet
- Cross-union queries can still skew too heavily toward single-union context
- Refusal answers can return spurious citations in some out-of-corpus cases

See [`docs/issues.md`](docs/issues.md) for the active roadmap and issue list.

## Documentation

- [`docs/planning.md`](docs/planning.md) — full project planning and architecture spec
- [`docs/architecture.md`](docs/architecture.md) — architecture index
- [`docs/github-workflow.md`](docs/github-workflow.md) — branch, PR, CI/CD, and release conventions
- [`docs/runbooks/ingestion.md`](docs/runbooks/ingestion.md) — ingestion operations
- [`docs/runbooks/deploy.md`](docs/runbooks/deploy.md) — deployment and rollback
- [`docs/runbooks/incident-response.md`](docs/runbooks/incident-response.md) — hotfix and incident handling
- [`docs/evaluation/phase1_results.md`](docs/evaluation/phase1_results.md) — latest evaluation output

## License

Released under the [MIT License](LICENSE).
