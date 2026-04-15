# EPSCAxplor — Project Planning & Architecture Document

A complete pre-development specification for the EPSCAxplor RAG-powered collective agreement
query platform. This document governs all architectural, data, and implementation decisions
before a line of production code is written.

**Status:** Pre-development planning
**Agreement period covered:** 2025–2030
**Last updated:** April 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Infrastructure Baseline](#2-infrastructure-baseline)
3. [Document Corpus & Taxonomy](#3-document-corpus--taxonomy)
4. [Data Architecture](#4-data-architecture)
5. [Service Architecture](#5-service-architecture)
6. [Ingestion Pipeline Specification](#6-ingestion-pipeline-specification)
7. [Query Pipeline Specification](#7-query-pipeline-specification)
8. [System Prompt Design](#8-system-prompt-design)
9. [API Design](#9-api-design)
10. [Multi-Tenancy & Auth](#10-multi-tenancy--auth)
11. [Evaluation Framework](#11-evaluation-framework)
12. [Repository Structure](#12-repository-structure)
13. [Development Phases](#13-development-phases)

---

## 1. Project Overview

### What EPSCAxplor Is

EPSCAxplor is a SaaS AI agent that allows construction industry professionals to query,
compare, and interpret collective agreements published under the EPSCA (Electrical Power
Systems Construction Association) framework in Ontario, Canada. It is powered by a hybrid
RAG architecture: local vector search for document retrieval and the Claude API for
grounded answer generation.

### The Problem

ICI (Industrial, Commercial, Institutional) construction projects in Ontario frequently
involve multiple trade unions working simultaneously on the same job site. Each union
operates under its own collective agreement governing overtime rates, foreman ratios,
tool allowances, jurisdictional boundaries, shift premiums, and grievance procedures.

Project managers, superintendents, and foremen must navigate up to 58 documents across
18 unions to answer questions that arise daily on the job. Manual searching is slow,
error-prone, and requires significant experience to interpret correctly. Errors lead
to grievances, labour disputes, and project delays.

### Success Criteria

Every answer EPSCAxplor produces must satisfy all four criteria:

1. **Grounded** — the answer is drawn exclusively from retrieved document content, not
   model inference or general knowledge.
2. **Cited** — every claim references the specific union, document title, article number,
   and section number it comes from.
3. **Versioned** — the response surfaces which agreement version and effective date the
   answer is based on.
4. **Disclaimed** — every response carries the standard legal disclaimer that the answer
   is for reference only and does not constitute legal advice.

An answer that does not meet all four criteria is a pipeline failure, not an acceptable
response.

### Target Users

| User Type | Primary Need |
|---|---|
| Foremen | Quick answers on shift premiums, overtime, tools for their specific agreement |
| Project Managers | Cross-union comparisons on the same question across multiple trades |
| Superintendents | Labour relations reference on large multi-trade projects |
| General Contractors | Compliance reference tool for field supervisors |
| Union Representatives | Verify contractors are correctly applying agreement terms |
| Union Administrators | Answer member entitlement questions |
| Union Stewards | On-the-job reference for grievance and compliance questions |
| Union Members | Understand their own entitlements, rates, and working conditions |

### Subscription Tiers

| Tier | Target | Access |
|---|---|---|
| Individual | Foremen, PMs, supers | Single user, monthly or annual |
| Professional | Small contractors, union locals | Up to 10 users, team features |
| Enterprise | GCs, large contractors, union halls | Unlimited users, white-label option, API access |

---

## 2. Infrastructure Baseline

### Reused VPS Infrastructure

EPSCAxplor is a clean new deployment on an existing VPS. The VPS previously hosted
services for a separate project (oTrak). No services, containers, databases, or
volumes from that project are carried into EPSCAxplor. The underlying VPS infrastructure
— Traefik, Dokploy, and Ollama — is reused; everything at the application layer is
net new.

| Component | Details | Role in EPSCAxplor |
|---|---|---|
| VPS | OVH VPS-3, 8 vCores, 24GB RAM, 200GB NVMe, Ubuntu 25.04 | Hosts all services |
| Reverse Proxy | Traefik v3 with automatic Let's Encrypt SSL | Routes all HTTP/HTTPS traffic |
| Deployment | Dokploy at deploy.boilerhaus.org | Docker Compose orchestration |
| Ollama | Running at http://127.0.0.1:11434 | Serves nomic-embed-text embeddings |

### Domain Strategy

| Environment | Domain | Notes |
|---|---|---|
| Development | `epscaxplor.boilerhaus.org` | Used during active development and internal testing |
| Production | TBD — dedicated product domain | Separate from boilerhaus.org; to be registered before go-to-market |

All subdomains during development nest under `epscaxplor.boilerhaus.org`. When the
production domain is registered, Traefik routing rules are updated and DNS is pointed
at the same VPS — no re-deployment of services required.

### Services to Deploy

All application services are new containers with no prior deployment history.

| Service | Purpose |
|---|---|
| `epsca-db` | Dedicated PostgreSQL 16 container for relational data |
| `epsca-qdrant` | Qdrant vector database for embeddings and metadata filtering |
| `epsca-api` | FastAPI backend — query engine, auth, tenant management |
| `epsca-web` | Next.js frontend — chat interface, citation UI, account management |

### Embedding Model

`nomic-embed-text` via the local Ollama instance at `http://127.0.0.1:11434`. This model
must be pulled before ingestion begins:

```bash
ollama pull nomic-embed-text
```

Output vector dimensions: **768**. This value is fixed and must be consistent across
the ingestion pipeline and Qdrant collection configuration.

### Generation Models

| Use Case | Model | Rationale |
|---|---|---|
| Standard single-union queries | `claude-haiku-4-5-20251001` | Fast, cost-effective with prompt caching |
| Complex cross-union comparisons | `claude-sonnet-4-6` | Superior instruction following for multi-document reasoning |

Prompt caching is enabled on all Claude API calls. The system prompt — which is identical
across all requests for a given query type — is cached, reducing effective input token
cost by approximately 90% on the repeated portion.

### Deployment Pattern

All new services follow the established Dokploy Docker Compose pattern:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.{name}.rule=Host(`{subdomain}.epscaxplor.boilerhaus.org`)"
  - "traefik.http.routers.{name}.entrypoints=websecure"
  - "traefik.http.routers.{name}.tls.certresolver=letsencrypt"
  - "traefik.http.services.{name}.loadbalancer.server.port={port}"
networks:
  - dokploy-network
```

> **Note:** Dollar signs in Docker Compose `basicauth` labels must be doubled (`$$`) for
> Traefik hash escaping.

---

## 3. Document Corpus & Taxonomy

### Complete Corpus Inventory

**Source:** https://www.epsca.org/resources
**Agreement cycle:** 2025–2030 (all documents current; no expired agreements in corpus)
**Total documents:** ~58

#### Primary Collective Agreements (20 documents)

| Union | Documents | Notes |
|---|---|---|
| Boilermakers | 1 CA | Single agreement |
| Brick and Allied Craft Union | 1 CA | Single agreement |
| Carpenters | 1 CA | Single agreement |
| Cement Masons | 1 CA | Single agreement |
| IBEW | 2 CA | Generation and Transmission are separate agreements |
| Insulators | 1 CA | Single agreement |
| Ironworkers | 1 CA | Single agreement |
| Labourers | 2 CA | Generation and Transmission are separate agreements |
| Millwrights | 1 CA | Single agreement |
| Operating Engineers | 1 CA | Single agreement |
| Painters | 1 CA | Single agreement |
| Plasterers | 1 CA | Single agreement |
| Rodmen | 1 CA | Single agreement |
| Roofers | 1 CA | Single agreement |
| Sheet Metal | 1 CA | Single agreement |
| Teamsters | 1 CA | Single agreement |
| Tile and Terrazzo | 1 CA | Single agreement |
| United Association | 1 CA | Single agreement |

#### Nuclear Project Agreements (16 documents)

All unions except BACU and Labourers have a Nuclear Project Agreement. These govern
work performed specifically on OPG and Bruce Power nuclear generation sites and may
override clauses in the Primary CA for nuclear project work.

| Union | NPA |
|---|---|
| Boilermakers | ✓ |
| Carpenters | ✓ |
| Cement Masons | ✓ |
| IBEW | ✓ |
| Insulators | ✓ |
| Ironworkers | ✓ |
| Millwrights | ✓ |
| Operating Engineers | ✓ |
| Painters | ✓ |
| Plasterers | ✓ |
| Rodmen | ✓ |
| Roofers | ✓ |
| Sheet Metal | ✓ |
| Teamsters | ✓ |
| Tile and Terrazzo | ✓ |
| United Association | ✓ |

#### Supplementary MOAs (2 documents)

| Document | Union | Date | Purpose |
|---|---|---|---|
| Appendix C Forepersons Rate MOA | Operating Engineers | 2021 | Modifies foreman rates in the main CA |
| Travel & Board MOA Updates | Painters | 2019 | Modifies travel and board provisions |

These MOAs are older than the current agreement cycle but remain in force.

#### Wage Schedules (18 documents)

One per union. Dynamically generated through the EPSCA website wage schedule selector
and downloaded manually as dated PDFs (e.g., `EPSCA Boilermakers - May 1, 2025.pdf`).

> **Important:** Wage schedule PDFs are dated independently of the main agreement.
> Wage rates are typically updated annually when contractual increases take effect.
> The effective date in the filename is the operative date, not the agreement start date.

#### OPG Reference Documents (2 documents)

| Document | Format | Purpose |
|---|---|---|
| OPG Wage Schedule Matrix | XLSX | Cross-trade wage reference tool for OPG sites |
| Wage Schedule Reference Guide | PDF | Quick reference for EPSCA wage schedule interpretation |

### Document Type Classifications

Every document in the corpus belongs to exactly one of these four types. This classification
drives retrieval behaviour and answer framing.

| Type Code | Description | Retrieval Behaviour |
|---|---|---|
| `primary_ca` | Primary Collective Agreement | Default for all queries |
| `nuclear_pa` | Nuclear Project Agreement | Included when query context is nuclear/OPG/Bruce Power |
| `moa_supplement` | MOA or Supplementary Agreement | Included when query matches affected topic and union |
| `wage_schedule` | Wage Schedule PDF | Primary source for classification and rate queries |

### The Nuclear Project Agreement Relationship

This is the most operationally important nuance in the corpus. When a user asks a question
about work performed on a nuclear project site, both the Primary CA and the Nuclear Project
Agreement must be retrieved and considered. The NPA may modify, supplement, or override
specific clauses in the primary agreement.

The query pipeline must handle this explicitly. A query containing site context such as
"Darlington", "Pickering", "Bruce Power", "OPG", or "nuclear" should automatically widen
retrieval to include the relevant NPA alongside the primary CA. The system prompt must
instruct Claude to surface conflicts or modifications between the two documents when both
are present in context.

---

## 4. Data Architecture

### PostgreSQL Schema (Relational Data)

The dedicated `epsca-db` PostgreSQL container stores all relational data: tenant and user
management, subscription enforcement, document registry, and query logging.

#### `tenants` Table

```sql
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,       -- URL-safe identifier, used for white-label routing
    tier            TEXT NOT NULL               -- 'individual', 'professional', 'enterprise'
                    CHECK (tier IN ('individual', 'professional', 'enterprise')),
    is_white_label  BOOLEAN NOT NULL DEFAULT FALSE,
    white_label_domain TEXT,                    -- Custom domain for white-label deployments
    corpus_filter   JSONB,                      -- Optional: restrict accessible unions for this tenant
                                                -- e.g. {"unions": ["IBEW", "Sheet Metal"]}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `users` Table

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'member'
                    CHECK (role IN ('owner', 'admin', 'member')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
```

#### `subscriptions` Table

```sql
CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tier            TEXT NOT NULL
                    CHECK (tier IN ('individual', 'professional', 'enterprise')),
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'cancelled', 'past_due', 'trialing')),
    stripe_customer_id      TEXT,
    stripe_subscription_id  TEXT,
    query_limit_monthly     INTEGER,            -- NULL means unlimited (enterprise)
    user_limit              INTEGER,            -- NULL means unlimited (enterprise)
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);
```

#### `api_keys` Table

```sql
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_hash        TEXT NOT NULL UNIQUE,       -- Store hash, never plaintext
    name            TEXT NOT NULL,             -- Human label, e.g. "Production API Key"
    last_used_at    TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_tenant_id ON api_keys(tenant_id);
```

#### `documents` Table

The document registry tracks every ingested document. This is the source of truth for
what is in the vector store, enabling re-ingestion, version tracking, and expiry flagging.

```sql
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    union_name      TEXT NOT NULL,             -- e.g. 'IBEW', 'Sheet Metal'
    document_type   TEXT NOT NULL              -- 'primary_ca', 'nuclear_pa', 'moa_supplement',
                    CHECK (document_type IN (  --   'wage_schedule'
                        'primary_ca',
                        'nuclear_pa',
                        'moa_supplement',
                        'wage_schedule'
                    )),
    agreement_scope TEXT,                      -- 'generation', 'transmission', or NULL
    title           TEXT NOT NULL,             -- Full document title as on EPSCA site
    source_url      TEXT,                      -- Original download URL (NULL for manually downloaded)
    source_filename TEXT NOT NULL,             -- Original filename
    effective_date  DATE,                      -- Agreement or wage schedule effective date
    expiry_date     DATE,                      -- Agreement expiry date (NULL if ongoing)
    is_expired      BOOLEAN NOT NULL DEFAULT FALSE,
    file_hash       TEXT NOT NULL,             -- SHA-256 of the PDF for change detection
    chunk_count     INTEGER,                   -- Populated after ingestion
    ingested_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_union_name ON documents(union_name);
CREATE INDEX idx_documents_document_type ON documents(document_type);
```

#### `query_logs` Table

Every query is logged for auditing, debugging, and future analytics.

```sql
CREATE TABLE query_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID REFERENCES users(id), -- NULL for API key queries
    query_text      TEXT NOT NULL,
    response_text   TEXT NOT NULL,
    model_used      TEXT NOT NULL,             -- 'claude-haiku-4-5' or 'claude-sonnet-4-6'
    union_filter    TEXT[],                    -- Unions filtered before retrieval, if any
    doc_type_filter TEXT[],                    -- Document types filtered, if any
    chunks_retrieved INTEGER NOT NULL,
    prompt_tokens   INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    latency_ms      INTEGER NOT NULL,
    citations       JSONB,                     -- Structured citation data extracted from response
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_query_logs_tenant_id ON query_logs(tenant_id);
CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at);
```

### Qdrant Schema (Vector Store)

Qdrant stores document chunks as vectors with rich payload metadata enabling pre-retrieval
filtering. All chunks live in a single collection.

#### Collection Configuration

```python
from qdrant_client.models import VectorParams, Distance

collection_config = {
    "collection_name": "epsca_chunks",
    "vectors_config": VectorParams(
        size=768,           # nomic-embed-text output dimensions
        distance=Distance.COSINE
    )
}
```

#### Point Payload Schema

Every point (chunk) stored in Qdrant carries the following payload:

| Field | Type | Description | Example |
|---|---|---|---|
| `union_name` | string | Canonical union name | `"IBEW"` |
| `document_id` | string (UUID) | Foreign key to `documents` table | `"abc123..."` |
| `document_type` | string | One of the four type codes | `"primary_ca"` |
| `agreement_scope` | string \| null | `"generation"`, `"transmission"`, or null | `"generation"` |
| `title` | string | Full document title | `"IBEW Generation 2025-2030 Collective Agreement"` |
| `effective_date` | string (ISO date) | Agreement or wage effective date | `"2025-05-01"` |
| `expiry_date` | string \| null | Agreement expiry date | `"2030-04-30"` |
| `is_expired` | bool | Whether this document is past its expiry | `false` |
| `article_number` | string \| null | Article number if identifiable | `"Article 12"` |
| `section_number` | string \| null | Section or clause number | `"12.03"` |
| `article_title` | string \| null | Article heading text | `"Overtime"` |
| `chunk_index` | int | Position of chunk within document | `42` |
| `chunk_text` | string | Full text of the chunk (stored for citation display) | `"..."` |
| `source_filename` | string | Original filename | `"IBEW Generation- 2025-2030 Collective Agreement.pdf"` |
| `page_number` | int \| null | Page number in source PDF | `18` |
| `is_table` | bool | Whether this chunk is extracted tabular data | `false` |

#### Filtering Strategy

Qdrant payload filtering runs before vector similarity scoring, which means filters have
zero impact on retrieval quality — they simply narrow the search space. The query pipeline
supports the following filter combinations:

- Filter by `union_name` for single-union targeted queries
- Filter by `document_type` to scope to primary CAs vs. NPAs vs. wage schedules
- Filter by `is_expired: false` on all queries (always applied)
- Filter by `agreement_scope` for IBEW/Labourers generation vs. transmission queries
- Combined `union_name` + `document_type` for precise scoping

---

## 5. Service Architecture

### Docker Services

```
┌─────────────────────────────────────────────────────────────────┐
│                        dokploy-network                          │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  epsca-web   │───▶│  epsca-api   │───▶│    epsca-db      │  │
│  │  (Next.js)   │    │  (FastAPI)   │    │  (PostgreSQL 16) │  │
│  │  :3000       │    │  :8000       │    │  :5432           │  │
│  └──────────────┘    └──────┬───────┘    └──────────────────┘  │
│                             │                                   │
│                             ├───────────▶┌──────────────────┐  │
│                             │            │  epsca-qdrant    │  │
│                             │            │  (Qdrant)        │  │
│                             │            │  :6333           │  │
│                             │            └──────────────────┘  │
│                             │                                   │
│                             └───────────▶ Ollama (host)         │
│                                          http://127.0.0.1:11434 │
└─────────────────────────────────────────────────────────────────┘
                              │
                         Traefik v3
                              │
                        Public internet
```

### Service Definitions

#### `epsca-api` (FastAPI Backend)

```yaml
services:
  epsca-api:
    image: epsca-api:${GIT_SHA}
    restart: unless-stopped
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - QDRANT_URL=http://epsca-qdrant:6333
      - OLLAMA_URL=http://host-gateway:11434
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - ENVIRONMENT=production
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.epsca-api.rule=Host(`api.epscaxplor.boilerhaus.org`)"
      - "traefik.http.routers.epsca-api.entrypoints=websecure"
      - "traefik.http.routers.epsca-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.epsca-api.loadbalancer.server.port=8000"
    extra_hosts:
      - "host-gateway:host-gateway"   # Allows container to reach host Ollama
    networks:
      - dokploy-network
```

#### `epsca-web` (Next.js Frontend)

```yaml
  epsca-web:
    image: epsca-web:${GIT_SHA}
    restart: unless-stopped
    environment:
      - NEXT_PUBLIC_API_URL=https://api.epscaxplor.boilerhaus.org
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.epsca-web.rule=Host(`epscaxplor.boilerhaus.org`)"
      - "traefik.http.routers.epsca-web.entrypoints=websecure"
      - "traefik.http.routers.epsca-web.tls.certresolver=letsencrypt"
      - "traefik.http.services.epsca-web.loadbalancer.server.port=3000"
    networks:
      - dokploy-network
```

#### `epsca-db` (PostgreSQL)

```yaml
  epsca-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=epsca
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - epsca-db-data:/var/lib/postgresql/data
    networks:
      - dokploy-network
    # Not exposed via Traefik — internal only
```

#### `epsca-qdrant` (Qdrant)

```yaml
  epsca-qdrant:
    image: qdrant/qdrant:latest
    restart: unless-stopped
    volumes:
      - epsca-qdrant-data:/qdrant/storage
    networks:
      - dokploy-network
    # Not exposed via Traefik — internal only
```

### Traefik Routing Summary

During development all public subdomains nest under `epscaxplor.boilerhaus.org`.
In production these routes are replaced with subdomains of the dedicated product domain.

| Subdomain (dev) | Service | Public |
|---|---|---|
| `epscaxplor.boilerhaus.org` | epsca-web | Yes |
| `api.epscaxplor.boilerhaus.org` | epsca-api | Yes |
| *(none)* | epsca-db (PostgreSQL) | No — internal only |
| *(none)* | epsca-qdrant (Qdrant) | No — internal only |

---

## 6. Ingestion Pipeline Specification

The ingestion pipeline is a Python script suite (`services/ingestion/`) that runs as a
one-time operation for initial corpus load and as a targeted re-run when documents are
updated. It is not a persistent service.

### Pipeline Stages

```
Download → Extract → Classify → Chunk → Embed → Store
```

### Stage 1: Download

**Script:** `download.py`

Downloads all corpus documents from EPSCA and stores them in a local `corpus/` directory
organized by union and document type.

```
corpus/
├── boilermakers/
│   ├── primary_ca/
│   │   └── Boilermakers - 2025 to 2030 Collective Agreement 20251024.pdf
│   └── nuclear_pa/
│       └── Boilermakers Nuclear Project Agreement.pdf
├── ibew/
│   ├── primary_ca/
│   │   ├── IBEW Generation- 2025-2030 Collective Agreement.pdf
│   │   └── IBEW Transmission - 2025-2030 Collective Agreement.pdf
│   └── nuclear_pa/
│       └── IBEW Nuclear Project Agreement.pdf
...
└── wage_schedules/
    ├── EPSCA Boilermakers - May 1, 2025.pdf
    ├── EPSCA IBEW - May 1, 2025.pdf
    ...
```

The download script also computes a SHA-256 hash of each downloaded file and compares it
against the `documents` table. If a file hash has changed since the last ingestion, it
marks the document for re-ingestion.

**Wage schedules** are manually downloaded from the EPSCA wage schedule selector and
placed in `corpus/wage_schedules/` before running the pipeline.

### Stage 2: Extract

**Script:** `extract.py`

Extracts text and structure from each PDF. Uses `pdfplumber` as the primary extraction
library because it preserves spatial layout and handles tables better than `pypdf`.

Two extraction modes:

**Prose extraction** (for CAs, NPAs, MOAs):
- Extract full text with page numbers
- Attempt to identify article headings using regex patterns common to EPSCA agreement
  formatting (e.g., `ARTICLE \d+`, `Section \d+\.\d+`)
- Preserve heading hierarchy as metadata alongside extracted text blocks

**Table extraction** (for wage schedules and wage schedule sections within CAs):
- Use `pdfplumber`'s table extraction to capture structured wage data
- Store extracted tables as JSON alongside page text
- Flag chunks extracted from tables with `is_table: true` in Qdrant payload

### Stage 3: Classify

**Script:** `classify.py`

Maps each document to its metadata using a configuration file (`corpus_manifest.yaml`)
that is hand-authored once and maintained as the corpus updates. The manifest defines
the canonical metadata for every document in the corpus:

```yaml
documents:
  - filename: "Boilermakers - 2025 to 2030 Collective Agreement 20251024.pdf"
    union_name: "Boilermakers"
    document_type: "primary_ca"
    agreement_scope: null
    effective_date: "2025-05-01"
    expiry_date: "2030-04-30"
    source_url: "https://www.epsca.org/upload/request/2?file=..."

  - filename: "IBEW Generation- 2025-2030 Collective Agreement.pdf"
    union_name: "IBEW"
    document_type: "primary_ca"
    agreement_scope: "generation"
    effective_date: "2025-05-01"
    expiry_date: "2030-04-30"
    source_url: "https://www.epsca.org/upload/request/5?file=..."
```

### Stage 4: Chunk

**Script:** `chunk.py`

Structure-aware chunking respects the article and section boundaries of EPSCA agreements.
Token-count-based splitting is a fallback only, not the primary strategy.

**Chunking rules:**

1. Attempt to split at article boundaries first (detected via heading patterns)
2. Within an article, split at section boundaries if the article exceeds the token limit
3. For sections that still exceed the token limit (~500 tokens), apply token-count
   splitting with a 50-token overlap
4. Never split mid-sentence
5. Table chunks are kept atomic — a wage table is one chunk regardless of size

**Chunk metadata attached at this stage:**
- `article_number` — parsed from the heading preceding the chunk
- `section_number` — parsed from the clause number preceding the chunk
- `article_title` — heading text
- `page_number` — page the chunk starts on
- `chunk_index` — sequential index within the document

### Stage 5: Embed

**Script:** `embed.py`

Calls the Ollama API to generate embeddings for each chunk using `nomic-embed-text`.

```python
import httpx

async def embed_chunk(text: str) -> list[float]:
    """
    Generate a 768-dimension embedding for a text chunk via Ollama.
    
    Args:
        text: The chunk text to embed.
    
    Returns:
        A list of 768 floats representing the embedding vector.
    """
    response = await httpx.AsyncClient().post(
        "http://127.0.0.1:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text}
    )
    return response.json()["embedding"]
```

Embeddings are generated in batches of 32 to avoid overwhelming the Ollama instance.
Each embedding is held in memory only long enough to be written to Qdrant.

### Stage 6: Store

**Script:** `store.py`

Writes each chunk as a Qdrant point and registers each document in the PostgreSQL
`documents` table.

The Qdrant point ID is a deterministic UUID derived from the document ID and chunk index,
ensuring that re-ingesting the same document with the same content is idempotent.

---

## 7. Query Pipeline Specification

### Query Flow

```
User question
     │
     ▼
Pre-processing (extract filters, detect nuclear context)
     │
     ▼
Embed question via Ollama nomic-embed-text
     │
     ▼
Qdrant filtered similarity search (k=6)
     │
     ▼
Context assembly (format chunks with citation headers)
     │
     ▼
Claude API call (Haiku or Sonnet based on query complexity)
     │
     ▼
Citation extraction from response
     │
     ▼
Log to PostgreSQL query_logs
     │
     ▼
Return structured response to user
```

### Step 1: Pre-processing

Before embedding the query, the pipeline performs lightweight analysis to determine
retrieval filters.

**Union detection:** If the user specifies a union by name (e.g., "under the IBEW
agreement"), set `union_filter` to restrict retrieval to that union only.

**Nuclear context detection:** If the query contains any of the following terms, set
`include_nuclear_pa: true` to widen retrieval to include Nuclear Project Agreements
alongside the primary CA:

```python
NUCLEAR_KEYWORDS = [
    "nuclear", "OPG", "Ontario Power Generation", "Bruce Power",
    "Darlington", "Pickering", "nuclear project", "NPA"
]
```

**Scope detection for IBEW/Labourers:** If the query mentions "generation" or
"transmission", set `agreement_scope` filter accordingly.

**Query complexity classification:** If the query contains cross-union comparison
language (e.g., "compare", "difference between", "all unions", "across trades"),
route to Claude Sonnet. Otherwise, use Haiku.

### Step 2: Retrieval

Retrieve `k=6` chunks from Qdrant. Qdrant filters applied before scoring:

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

def build_filter(
    union_filter: str | None,
    include_nuclear_pa: bool,
    agreement_scope: str | None
) -> Filter:
    conditions = [
        FieldCondition(key="is_expired", match=MatchValue(value=False))
    ]
    
    if union_filter:
        conditions.append(
            FieldCondition(key="union_name", match=MatchValue(value=union_filter))
        )
    
    if not include_nuclear_pa:
        # Default: exclude NPAs unless nuclear context detected
        conditions.append(
            FieldCondition(key="document_type", match=MatchValue(value="primary_ca"))
        )
    
    if agreement_scope:
        conditions.append(
            FieldCondition(key="agreement_scope", match=MatchValue(value=agreement_scope))
        )
    
    return Filter(must=conditions)
```

### Step 3: Context Assembly

Retrieved chunks are assembled into a structured context block passed to Claude.
Each chunk is wrapped in a citation header so Claude can reference it precisely:

```
[SOURCE 1]
Union: IBEW
Document: IBEW Generation 2025-2030 Collective Agreement
Document Type: Primary Collective Agreement
Effective: May 1, 2025 | Expires: April 30, 2030
Article 12 — Overtime | Section 12.03
Page: 34

"[chunk text here]"

---

[SOURCE 2]
...
```

### Step 4: Model Selection and Routing

```python
def select_model(is_cross_union: bool) -> str:
    """Select the appropriate Claude model based on query complexity."""
    if is_cross_union:
        return "claude-sonnet-4-6"
    return "claude-haiku-4-5-20251001"
```

### Step 5: Response Structure

The API returns a structured JSON response:

```json
{
  "answer": "string — the generated answer text",
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
      "excerpt": "string — relevant clause text"
    }
  ],
  "model_used": "claude-haiku-4-5-20251001",
  "disclaimer": "This answer is for reference only and does not constitute legal advice. Consult qualified labour relations counsel for binding interpretations.",
  "query_log_id": "uuid"
}
```

---

## 8. System Prompt Design

The system prompt is the most important quality control mechanism in the pipeline. It
is identical across all requests of the same type, enabling prompt caching.

### Standard Query System Prompt

```
You are EPSCAxplor, a specialist reference assistant for EPSCA collective agreements 
covering construction trade unions in Ontario, Canada.

Your job is to answer questions about collective agreement terms, wages, working 
conditions, and labour relations using only the source documents provided in this 
conversation. You do not use general knowledge. You do not guess. You do not infer 
beyond what the documents state.

CITATION RULES — these are non-negotiable:

1. Every factual claim in your answer must be attributed to a specific source using 
   the format [SOURCE N] where N matches the source number in the provided context.

2. You must identify the specific article and section number for every cited claim. 
   If a source does not clearly show an article or section number, cite the document 
   title and page number instead.

3. If two sources say different things about the same topic (for example, a Primary CA 
   and a Nuclear Project Agreement), you must surface the conflict explicitly and explain 
   which document governs which context.

4. Never combine information from multiple sources into a single unattributed statement.

REFUSAL RULES:

5. If the answer to a question is not present in the provided sources, say so directly: 
   "The provided documents do not contain information about [topic]." Do not speculate 
   or draw on general knowledge to fill the gap.

6. If the question requires a legal interpretation or advice about which party is right 
   in a dispute, decline to make that determination. Provide the relevant clause text 
   and note that interpretation is a matter for qualified labour relations counsel.

ANSWER FORMAT:

- Lead with a direct answer to the question.
- Follow with the supporting clause text and citation.
- End every response with this exact disclaimer on its own line:
  "⚠️ This answer is for reference only and does not constitute legal advice."

Provided sources follow.
```

### Cross-Union Comparison System Prompt

Used when `is_cross_union: true`. Adds explicit comparison instructions:

```
[Standard prompt above, with this section appended before "Provided sources follow."]

COMPARISON RULES:

When comparing provisions across multiple unions:
- Address each union's position separately before summarizing differences.
- Use a consistent structure: [Union Name]: [provision], citing [SOURCE N].
- If a union's agreement is silent on a topic that other agreements address explicitly, 
  note the absence — do not assume the provision does not exist.
```

---

## 9. API Design

### Base URL

```
https://api.epscaxplor.boilerhaus.org/v1
```

### Authentication

All endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <jwt_or_api_key>
```

### Endpoints

#### `POST /query`

Submit a natural language query against the corpus.

**Request body:**

```json
{
  "question": "string (required) — the natural language question",
  "union_filter": "string (optional) — restrict to a specific union name",
  "document_type_filter": ["string"] // optional — restrict to specific document types
}
```

**Response:** See structured response in Section 7, Step 5.

**Error responses:**

| Status | Code | Description |
|---|---|---|
| 400 | `invalid_request` | Missing or malformed `question` field |
| 401 | `unauthorized` | Missing or invalid auth token |
| 429 | `rate_limited` | Monthly query limit reached for this subscription tier |
| 503 | `upstream_error` | Claude API or Qdrant unavailable |

---

#### `GET /documents`

List all documents in the corpus registry.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `union_name` | string | Filter by union |
| `document_type` | string | Filter by document type code |
| `is_expired` | boolean | Filter by expiry status |

**Response:**

```json
{
  "documents": [
    {
      "id": "uuid",
      "union_name": "IBEW",
      "document_type": "primary_ca",
      "title": "IBEW Generation 2025-2030 Collective Agreement",
      "effective_date": "2025-05-01",
      "expiry_date": "2030-04-30",
      "is_expired": false,
      "chunk_count": 312,
      "ingested_at": "2026-04-15T10:00:00Z"
    }
  ],
  "total": 58
}
```

---

#### `GET /query-history`

Retrieve the authenticated user's query history.

**Query parameters:** `limit` (default 20), `offset` (default 0)

**Response:** Paginated list of past queries with answers and citations.

---

#### `GET /health`

Health check endpoint. Returns 200 if all dependencies are reachable.

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

---

## 10. Multi-Tenancy & Auth

### Tenant Model

Every request operates within a tenant context. The tenant determines:

- Which users are authorized
- What subscription tier applies (rate limits, user limits)
- Whether corpus filtering is in effect (enterprise white-label tenants may be
  restricted to specific unions)
- Which query logs belong to this account

Tenant context is extracted from the JWT or API key on every request and injected
into all downstream database queries and query logs.

### Authentication Flow

**Session users (web app):**

1. User submits email + password to `POST /auth/login`
2. API validates against `users` table (bcrypt password comparison)
3. Returns a short-lived JWT (15 minutes) and a longer-lived refresh token (7 days)
4. Frontend stores JWT in memory, refresh token in httpOnly cookie
5. All subsequent requests include JWT as Bearer token

**API key users (enterprise tier):**

1. Enterprise admin generates an API key via the dashboard
2. API key is displayed once; only its SHA-256 hash is stored in `api_keys` table
3. Requests include the raw key as Bearer token
4. API hashes the incoming key, looks up the hash in `api_keys`, extracts tenant context

### Rate Limiting

Rate limits are enforced per tenant, not per user. Limits are checked at the start
of every query request against the `subscriptions` table.

| Tier | Monthly Query Limit | User Limit |
|---|---|---|
| Individual | TBD | 1 |
| Professional | TBD | 10 |
| Enterprise | Unlimited | Unlimited |

When a tenant reaches their monthly limit, subsequent queries return `429 rate_limited`
until the subscription period resets.

---

## 11. Evaluation Framework

Evaluation is designed before coding, not after. The gold question set drives
acceptance criteria at each development phase.

### Gold Question Set

A set of 60 questions with known correct answers, drawn from actual contract language.
Organized by question type:

**Wages & Rates (15 questions)**
- "What is the journeyperson hourly rate for a Boilermaker as of May 1, 2025?"
- "What is the foreman premium for Sheet Metal workers?"
- "How much is the tool allowance for IBEW electricians?"

**Overtime & Hours (15 questions)**
- "What constitutes overtime for Ironworkers?"
- "What is the overtime multiplier for Carpenters on a Saturday?"
- "What are the daily overtime rules for Operating Engineers?"

**Travel & Board (10 questions)**
- "What is the board allowance for Millwrights working away from home?"
- "How is travel time compensated for United Association plumbers?"

**Nuclear Project Specific (10 questions)**
- "Are there different overtime rules for Boilermakers working on a nuclear project?"
- "What additional provisions apply to IBEW electricians at Darlington?"

**Cross-Union Comparisons (10 questions)**
- "Compare the overtime rules for IBEW and Sheet Metal workers"
- "Which union has the highest journeyperson base rate as of May 2025?"
- "How do Millwrights and Operating Engineers differ on foreman ratios?"

### Evaluation Metrics

Each response is scored against four dimensions:

| Metric | Description | Pass Threshold |
|---|---|---|
| **Correctness** | Answer matches the known correct answer | Exact match or equivalent |
| **Citation accuracy** | Article/section cited actually contains the claimed information | 100% — zero tolerance |
| **Citation completeness** | All factual claims are cited | All claims attributed |
| **Refusal behaviour** | System declines to answer when information is absent | Declines correctly, no hallucination |

### POC Acceptance Criteria

Before proceeding from Phase 1 (POC) to Phase 2 (full corpus), the pipeline must
score against the first three unions (IBEW Generation, Sheet Metal, United Association):

- Correctness ≥ 85% on questions covering those three unions
- Citation accuracy = 100% (zero tolerance for phantom citations)
- Zero hallucinated facts on refusal-type questions

---

## 12. Repository Structure

```
epscaxplor/
├── apps/
│   └── web/                    # Next.js frontend
│       ├── src/
│       │   ├── app/            # App Router pages
│       │   ├── components/     # UI components
│       │   └── lib/            # API client, auth helpers
│       ├── Dockerfile
│       └── package.json
│
├── services/
│   ├── api/                    # FastAPI backend
│   │   ├── src/
│   │   │   ├── routes/         # API route handlers
│   │   │   ├── rag/            # Query pipeline logic
│   │   │   ├── auth/           # JWT and API key auth
│   │   │   ├── db/             # PostgreSQL models and queries
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── ingestion/              # One-time ingestion pipeline
│       ├── corpus/             # Downloaded PDFs (gitignored)
│       ├── corpus_manifest.yaml # Document metadata registry
│       ├── download.py
│       ├── extract.py
│       ├── classify.py
│       ├── chunk.py
│       ├── embed.py
│       ├── store.py
│       ├── run_pipeline.py     # Orchestrates all stages
│       └── requirements.txt
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml       # Production stack
│   │   └── docker-compose.dev.yml   # Local development overrides
│   └── db/
│       └── migrations/         # SQL migration files
│
└── docs/
    ├── planning.md             # This document
    ├── architecture.md         # Architecture diagrams
    └── runbooks/               # Operational runbooks
```

---

## 13. Development Phases

### Phase 0 — Foundation

**Goal:** Running infrastructure, empty but functional services.

**Tasks:**
- Remove Nextcloud and Mistral 7B from VPS
- Pull `nomic-embed-text` into Ollama
- Deploy `epsca-db` PostgreSQL container via Dokploy
- Run database migrations (create all tables from Section 4)
- Deploy `epsca-qdrant` container via Dokploy
- Create `epsca_chunks` collection in Qdrant
- Verify inter-service connectivity (API can reach DB, Qdrant, and Ollama)

**Completion criteria:**
- `GET /health` returns `{"status": "ok"}` with all dependencies green
- Can INSERT and SELECT from all PostgreSQL tables
- Can create and query a test point in Qdrant

---

### Phase 1 — Proof of Concept

**Goal:** End-to-end working pipeline validated against 3 unions before scaling.

**Target unions:** IBEW Generation, Sheet Metal, United Association

**Tasks:**
- Author `corpus_manifest.yaml` entries for the 3 POC unions
- Download and process 6 documents (3 primary CAs + 3 NPAs)
- Build and run ingestion pipeline for POC corpus
- Build query endpoint (`POST /query`)
- Implement basic JWT auth (no subscription enforcement yet)
- Test against gold question set questions covering the 3 POC unions
- Verify citation accuracy manually against source PDFs

**Completion criteria:**
- Correctness ≥ 85% on POC gold questions
- Citation accuracy = 100%
- Cross-union comparison query works for IBEW vs. Sheet Metal
- Nuclear context detection correctly widens retrieval to NPA

---

### Phase 2 — Full Corpus

**Goal:** All 58 documents ingested and queryable.

**Tasks:**
- Complete `corpus_manifest.yaml` for all 18 unions
- Download all remaining documents (manually for wage schedules)
- Run full ingestion pipeline
- Test against full gold question set
- Refine chunking strategy based on observed retrieval quality issues
- Implement wage schedule query handling (table extraction validation)

**Completion criteria:**
- All 58 documents ingested with no extraction failures
- Full gold question set scores meet Phase 1 thresholds across all unions
- Wage rate queries return correct figures with accurate citations

---

### Phase 3 — Product Layer

**Goal:** Secure, multi-tenant product ready for beta users.

**Tasks:**
- Complete auth system (JWT + refresh tokens + API keys)
- Subscription tier enforcement (rate limiting)
- Query history endpoint
- Frontend chat interface with citation display
- Legal disclaimer prominent in UI and every response
- `GET /documents` endpoint for corpus browser UI

**Completion criteria:**
- Multi-tenant isolation verified (tenant A cannot see tenant B's query history)
- Rate limiting correctly enforces tier limits
- Citation UI displays source document, article, and section for every claim
- Legal disclaimer visible on every answer

---

### Phase 4 — Go to Market

**Goal:** Paid product with billing and white-label capability.

**Tasks:**
- Stripe subscription integration
- Pricing page and checkout flow
- White-label configuration (custom domain routing via Traefik, logo/brand customization)
- Enterprise API key management dashboard
- Marketing site at product domain (separate from boilerhaus.org)
- Terms of service and privacy policy
- Confirm EPSCA document usage rights before public launch

**Completion criteria:**
- End-to-end subscription purchase and tier enforcement working
- White-label tenant can access EPSCAxplor under their own domain
- Enterprise API key can authenticate and query without session login
