# EPSCAxplor — GitHub Workflow & Repository Guide

Reference document for branch strategy, commit conventions, CI/CD pipeline design,
environment configuration, and release management. Covers the full development lifecycle
from local work to production deployment via Dokploy on the OVH VPS.

**Repository:** `epscaxplor` (monorepo)
**Environment:** Docker / self-hosted / Dokploy + Traefik
**Developer context:** Solo developer with AI-assisted development practices
**Last updated:** April 2026

---

## Table of Contents

1. [Repository Structure](#1-repository-structure)
2. [Branch Strategy](#2-branch-strategy)
3. [Commit Conventions](#3-commit-conventions)
4. [Pull Request Conventions](#4-pull-request-conventions)
5. [CI/CD Pipeline](#5-cicd-pipeline)
6. [Environment Configuration](#6-environment-configuration)
7. [Release Management](#7-release-management)
8. [Incident Response](#8-incident-response)

---

## 1. Repository Structure

The repository is organized as a monorepo with five top-level lanes. Each lane has a
distinct change cadence and blast radius. Changes should stay within a single lane
wherever possible — cross-lane PRs require explicit justification.

```
epscaxplor/
├── apps/
│   └── web/                    # Next.js frontend (chat UI, citation display, account management)
│       ├── src/
│       │   ├── app/            # App Router pages
│       │   ├── components/     # UI components
│       │   └── lib/            # API client, auth helpers
│       ├── Dockerfile
│       └── package.json
│
├── services/
│   ├── api/                    # FastAPI backend (query engine, auth, tenant management)
│   │   ├── src/
│   │   │   ├── routes/         # API route handlers
│   │   │   ├── rag/            # Query pipeline logic
│   │   │   ├── auth/           # JWT and API key auth
│   │   │   ├── db/             # PostgreSQL models and queries
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── ingestion/              # One-time ingestion pipeline (not a persistent service)
│       ├── corpus/             # Downloaded PDFs — gitignored
│       ├── corpus_manifest.yaml
│       ├── download.py
│       ├── extract.py
│       ├── classify.py
│       ├── chunk.py
│       ├── embed.py
│       ├── store.py
│       ├── run_pipeline.py     # Orchestrates all pipeline stages
│       └── requirements.txt
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml       # Production stack
│   │   └── docker-compose.dev.yml   # Local development overrides
│   └── db/
│       └── migrations/              # SQL migration files (numbered sequentially)
│
└── docs/
    ├── planning.md                  # Project planning and architecture document
    ├── architecture.md              # Architecture diagrams
    ├── github-workflow.md           # This document
    └── runbooks/                    # Operational runbooks
        ├── ingestion.md
        ├── deploy.md
        └── incident-response.md
```

### Lane Responsibilities and Blast Radius

| Lane | Change Cadence | Blast Radius | Notes |
|---|---|---|---|
| `apps/` | High | Contained | UI changes. Broken frontend doesn't affect the API. |
| `services/` | Moderate | High | API or ingestion bugs affect all users. |
| `infra/` | Low | Highest | Misconfigured Traefik or Docker Compose can bring down all services. |
| `docs/` | As needed | None | Documentation only. |

The `ingestion/` service is not a persistent container. It runs as a one-time operation.
Changes to it do not require the same deployment rigour as `api/` or `web/`.

---

## 2. Branch Strategy

EPSCAxplor uses a simplified trunk-based development model appropriate for a solo
developer. There is one permanent protected branch (`main`) and short-lived feature
branches for all work.

### Branch Model

```
main                    ← production-ready, always deployable
  └── feat/my-feature   ← short-lived, branched from main, merged back to main
  └── fix/my-fix
  └── chore/my-task
  └── release/v1.2.0    ← cut from main, exists only for the release window
```

There is no persistent `staging` or `develop` branch. The development domain
(`epscaxplor.boilerhaus.org`) is the staging environment, deployed from `main` on
every merge. The production domain (to be registered before go-to-market) is deployed
from tagged releases on `main`.

### Branch Naming

All branches follow the pattern `<type>/<short-description>` using lowercase kebab-case.

| Prefix | Purpose | Example |
|---|---|---|
| `feat/` | New feature or capability | `feat/qdrant-ingestion-pipeline` |
| `fix/` | Bug fix | `fix/nuclear-keyword-detection` |
| `chore/` | Maintenance, deps, config | `chore/update-anthropic-sdk` |
| `docs/` | Documentation only | `docs/api-reference-v1` |
| `release/` | Release preparation | `release/v0.2.0` |

### Branch Lifetime

Feature branches should live no longer than a few days. If a branch has been open for
a week without merging, that is a signal to break the work down into smaller increments
or use a feature flag to ship the partial work safely.

### Branch Protections

Apply the following protections to `main` via GitHub repository settings:

- Require pull request before merging (no direct pushes, including from the repo owner)
- Require status checks to pass before merging (CI must be green)
- Require branches to be up to date before merging
- Do not allow bypassing the above settings

These rules apply even when working solo. Bypassing them under time pressure is how
production regressions get introduced.

---

## 3. Commit Conventions

EPSCAxplor uses Conventional Commits. This standard enables automated changelog
generation and keeps `git log` readable without manual maintenance.

### Format

```
<type>(<scope>): <short description>

[optional body — explain why, not what]

[optional footer — breaking changes, issue references]
```

The short description is lowercase, imperative mood, no trailing period, under 72 characters.

### Types

| Type | When to Use |
|---|---|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `chore` | Maintenance: dependency updates, config changes, build tooling |
| `refactor` | Code restructuring with no behaviour change |
| `test` | Adding or updating tests |
| `perf` | Performance improvement |
| `ci` | CI/CD pipeline changes |

### Scopes

Scopes are optional but recommended for monorepo clarity. Use the service or lane name.

| Scope | Covers |
|---|---|
| `api` | FastAPI backend |
| `web` | Next.js frontend |
| `ingestion` | Ingestion pipeline scripts |
| `infra` | Docker Compose, Traefik config |
| `db` | Database migrations or schema |
| `rag` | RAG query pipeline logic |
| `auth` | Authentication and tenant logic |

### Examples

```
feat(ingestion): add structure-aware chunking for EPSCA article boundaries

fix(rag): correct nuclear keyword detection for Bruce Power queries

chore(api): pin anthropic sdk to 0.21.0

feat(auth): implement JWT refresh token rotation

docs: add ingestion pipeline runbook

ci: add docker layer caching to build workflow

feat(db)!: add tenant corpus_filter column to tenants table

BREAKING CHANGE: existing tenants require a migration before queries will succeed
```

### Merge Strategy

All PRs are merged using **squash and merge**. This keeps the `main` history clean —
one logical commit per PR rather than a stream of intermediate `wip:` and `fix typo`
commits. The squashed commit message should follow Conventional Commits format using
the PR title (the PR title is therefore the canonical commit message — write it well).

---

## 4. Pull Request Conventions

Every change to `main` passes through a pull request. No exceptions.

### PR Title

The PR title becomes the squashed commit message on `main`. It must follow Conventional
Commits format exactly:

```
feat(rag): implement Qdrant filtered similarity search with nuclear context detection
```

### PR Description Template

Save the following as `.github/pull_request_template.md` in the repository root.
GitHub will pre-populate it for every new PR.

```markdown
## Summary
<!-- One to three sentences. What does this PR do and why? -->

## Scope
<!-- Which lanes are touched (apps/, services/, infra/, docs/)? -->
<!-- If this is a cross-lane PR, explain why the coupling is necessary. -->

## Validation
<!-- How do you know this works? -->
<!-- List: manual smoke test steps, CI checks, curl examples, etc. -->

## Risk
<!-- Blast radius. What breaks if this is wrong? -->
<!-- Data migrations, environment variable requirements, service restarts needed? -->

## Rollback
<!-- How do you revert this if something goes wrong post-merge? -->
<!-- "Revert the PR" is acceptable for most cases — note any exceptions. -->

## Related Issues
<!-- Closes #N -->
```

### Issue Linkage

Every PR must reference an open GitHub Issue. If no issue exists, create one before
opening the PR. The issue is the decision record — it captures why the work is being
done. The PR is the execution record — it captures how.

For solo development with AI assistance, this discipline is especially important.
AI-generated code moves fast. Issues provide the audit trail that makes it possible to
understand later why a particular approach was chosen.

### PR Size

A good PR is reviewable in under 15 minutes. In practice for this project, that means:

- One primary concern per PR (one feature, one fix, one refactor)
- Cross-lane changes are split: land the foundation first, the consumer in a follow-up
- Infra PRs are as small as possible — separate config changes from structural changes

If a feature is too large for a single PR, use a feature branch with stacked PRs, or
use a feature flag to ship the scaffolding before the capability.

### Self-Review Checklist

Before marking a PR ready for merge, verify:

- [ ] PR title follows Conventional Commits format
- [ ] All required description fields are filled in (Summary, Scope, Validation, Risk, Rollback)
- [ ] CI checks are green
- [ ] New environment variables are documented in `.env.example`
- [ ] Any new database columns have a migration file in `infra/db/migrations/`
- [ ] Code has inline comments explaining non-obvious decisions
- [ ] The branch is up to date with `main`

---

## 5. CI/CD Pipeline

GitHub Actions handles all CI/CD. The pipeline has three concerns: **validate**,
**build**, and **deploy**. These run as separate jobs within a workflow to make
failures easy to pinpoint.

### Trigger Summary

| Trigger | Workflow | What Runs |
|---|---|---|
| Push to any feature branch | `ci.yml` | Validate only (lint, type-check, tests) |
| Merge to `main` | `deploy-dev.yml` | Validate → Build → Deploy to dev environment |
| Push of a version tag (`v*.*.*`) | `deploy-prod.yml` | Validate → Build → Deploy to production |

### Workflow: `ci.yml` — Validate on Feature Branches

This workflow runs on every push to a non-`main` branch. Its sole job is to catch
regressions before they reach `main`. It should complete in under 3 minutes.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches-ignore:
      - main

jobs:
  validate-api:
    name: Validate API
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: services/api/requirements.txt

      - name: Install dependencies
        run: pip install -r services/api/requirements.txt

      - name: Lint
        run: ruff check services/api/src/

      - name: Type check
        run: mypy services/api/src/

      - name: Run tests
        run: pytest services/api/tests/ -v

  validate-web:
    name: Validate Web
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: apps/web/package-lock.json

      - name: Install dependencies
        working-directory: apps/web
        run: npm ci

      - name: Type check
        working-directory: apps/web
        run: npm run type-check

      - name: Lint
        working-directory: apps/web
        run: npm run lint
```

### Workflow: `deploy-dev.yml` — Build and Deploy to Dev on Merge to Main

This workflow triggers on every merge to `main`. It builds Docker images tagged with
the Git SHA, pushes them to the GitHub Container Registry (GHCR), and triggers a
Dokploy redeploy via webhook.

```yaml
# .github/workflows/deploy-dev.yml
name: Deploy to Dev

on:
  push:
    branches:
      - main

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ghcr.io/${{ github.repository_owner }}/epscaxplor

jobs:
  validate:
    # Reuse the same validation steps as ci.yml
    # In practice, extract into a reusable workflow (.github/workflows/validate.yml)
    # and call it with `uses:` here to avoid duplication.
    name: Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate API
        run: |
          pip install -r services/api/requirements.txt
          ruff check services/api/src/
          mypy services/api/src/
      - name: Validate Web
        run: |
          cd apps/web && npm ci && npm run type-check && npm run lint

  build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: validate
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: services/api
          push: true
          # Tag with both the Git SHA (immutable, for rollback) and 'latest' (for convenience)
          tags: |
            ${{ env.IMAGE_PREFIX }}-api:${{ github.sha }}
            ${{ env.IMAGE_PREFIX }}-api:latest
          # Cache layers from the previous build to keep CI fast
          cache-from: type=registry,ref=${{ env.IMAGE_PREFIX }}-api:buildcache
          cache-to: type=registry,ref=${{ env.IMAGE_PREFIX }}-api:buildcache,mode=max

      - name: Build and push Web image
        uses: docker/build-push-action@v5
        with:
          context: apps/web
          push: true
          tags: |
            ${{ env.IMAGE_PREFIX }}-web:${{ github.sha }}
            ${{ env.IMAGE_PREFIX }}-web:latest
          cache-from: type=registry,ref=${{ env.IMAGE_PREFIX }}-web:buildcache
          cache-to: type=registry,ref=${{ env.IMAGE_PREFIX }}-web:buildcache,mode=max

  deploy:
    name: Deploy to Dev
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Trigger Dokploy redeploy — API
        run: |
          curl -s -o /dev/null -w "%{http_code}" \
            -X POST "${{ secrets.DOKPLOY_WEBHOOK_API }}" \
            -H "Authorization: Bearer ${{ secrets.DOKPLOY_TOKEN }}"

      - name: Trigger Dokploy redeploy — Web
        run: |
          curl -s -o /dev/null -w "%{http_code}" \
            -X POST "${{ secrets.DOKPLOY_WEBHOOK_WEB }}" \
            -H "Authorization: Bearer ${{ secrets.DOKPLOY_TOKEN }}"
```

> **Note on Dokploy webhooks:** Each application in Dokploy exposes a deploy webhook
> URL. Store these as `DOKPLOY_WEBHOOK_API` and `DOKPLOY_WEBHOOK_WEB` in GitHub
> Actions secrets. Dokploy will pull the latest image from GHCR and restart the
> container when the webhook fires. The `GIT_SHA` environment variable passed to
> the Docker Compose stack should be updated in Dokploy's environment config to
> match the deployed SHA.

### Workflow: `deploy-prod.yml` — Deploy to Production on Version Tag

Production deploys are triggered by pushing a semantic version tag (e.g., `v0.2.0`).
This workflow is identical to `deploy-dev.yml` but targets the production Dokploy
webhooks and fires only on tag pushes.

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy to Production

on:
  push:
    tags:
      - "v*.*.*"

# ... same jobs as deploy-dev.yml but using production webhook secrets:
# DOKPLOY_PROD_WEBHOOK_API, DOKPLOY_PROD_WEBHOOK_WEB
```

### Required GitHub Actions Secrets

Configure these in the repository under **Settings → Secrets and variables → Actions**.

| Secret Name | Value |
|---|---|
| `DOKPLOY_TOKEN` | Dokploy API token (dev environment) |
| `DOKPLOY_WEBHOOK_API` | Dokploy deploy webhook URL for `epsca-api` (dev) |
| `DOKPLOY_WEBHOOK_WEB` | Dokploy deploy webhook URL for `epsca-web` (dev) |
| `DOKPLOY_PROD_WEBHOOK_API` | Dokploy deploy webhook URL for `epsca-api` (prod) |
| `DOKPLOY_PROD_WEBHOOK_WEB` | Dokploy deploy webhook URL for `epsca-web` (prod) |

The `GITHUB_TOKEN` secret is automatically provided by GitHub Actions and does not
need to be configured manually. It is used for pushing to GHCR.

---

## 6. Environment Configuration

### The Four Environments

| Environment | Domain | Deployed From | Purpose |
|---|---|---|---|
| Local dev | `localhost` | Developer machine | Day-to-day development |
| Dev / staging | `epscaxplor.boilerhaus.org` | Merge to `main` | Integration testing, demos |
| Production | TBD product domain | Version tag push | Live users |

### File Layout

```
.env.example        # Committed — all required keys with placeholder values and comments
.env.local          # Gitignored — developer's local values
.env.dev            # Gitignored — dev environment values (or managed via Dokploy UI)
.env.production     # Never stored on disk — injected at deploy time via Dokploy
```

The `.env.example` file is the authoritative list of all environment variables. It must
be updated whenever a new variable is added. A PR that introduces a new env var without
updating `.env.example` should not merge.

### `.env.example` — Full Variable Reference

```bash
# ─── Database ────────────────────────────────────────────────────────────────
# PostgreSQL connection string for the epsca-db container
DATABASE_URL=postgresql://user:password@epsca-db:5432/epsca

# ─── Vector Store ────────────────────────────────────────────────────────────
# Qdrant REST API base URL (internal Docker network)
QDRANT_URL=http://epsca-qdrant:6333

# ─── Embeddings ──────────────────────────────────────────────────────────────
# Ollama API base URL — uses host-gateway to reach the host from inside a container
OLLAMA_URL=http://host-gateway:11434
OLLAMA_EMBED_MODEL=nomic-embed-text

# ─── Claude API ──────────────────────────────────────────────────────────────
# Anthropic API key — never commit this value
ANTHROPIC_API_KEY=sk-ant-...

# Model identifiers — configurable to allow model upgrades without code changes
CLAUDE_HAIKU_MODEL=claude-haiku-4-5-20251001
CLAUDE_SONNET_MODEL=claude-sonnet-4-6

# ─── Auth ────────────────────────────────────────────────────────────────────
# Secret used to sign and verify JWTs — generate with: openssl rand -hex 32
JWT_SECRET=replace-with-random-hex-string

# JWT expiry durations (in seconds unless otherwise noted)
JWT_ACCESS_EXPIRY_SECONDS=900         # 15 minutes
JWT_REFRESH_EXPIRY_DAYS=7             # 7 days

# ─── Application ─────────────────────────────────────────────────────────────
# Runtime environment — controls log verbosity, debug tooling, error detail in responses
ENVIRONMENT=development               # development | production

# CORS allowed origins — comma-separated list
CORS_ORIGINS=http://localhost:3000

# ─── Frontend (Next.js) ──────────────────────────────────────────────────────
# Public API base URL — baked into the Next.js build at compile time
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Environment Validation at Startup

The FastAPI application validates all required environment variables at startup using
Pydantic Settings. If a required variable is missing or malformed, the application
fails immediately with a clear error rather than starting in a broken state.

```python
# services/api/src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    Pydantic will raise a ValidationError at startup if any required field
    is missing, preventing silent misconfiguration in production.
    """
    database_url: str
    qdrant_url: str
    ollama_url: str
    ollama_embed_model: str = "nomic-embed-text"
    anthropic_api_key: str
    claude_haiku_model: str = "claude-haiku-4-5-20251001"
    claude_sonnet_model: str = "claude-sonnet-4-6"
    jwt_secret: str
    jwt_access_expiry_seconds: int = 900
    jwt_refresh_expiry_days: int = 7
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env.local"
        case_sensitive = False

settings = Settings()
```

---

## 7. Release Management

Releases are intentional but lightweight. The goal is traceability and the ability to
roll back any production deploy to the previous known-good state within a few minutes.

### Semantic Versioning

EPSCAxplor uses semantic versioning: `MAJOR.MINOR.PATCH`.

- **PATCH** (`v0.1.1`) — Bug fixes, documentation updates, dependency patches. No new
  behaviour.
- **MINOR** (`v0.2.0`) — New features, new API endpoints, new document corpus additions.
  Backward compatible.
- **MAJOR** (`v1.0.0`) — Breaking API changes, significant architectural changes, or the
  initial public launch.

### Release Process

**Step 1 — Verify dev environment.** Confirm the current `main` is healthy on the dev
domain. Run through the smoke test checklist (see below). Do not cut a release from a
broken `main`.

**Step 2 — Update the changelog.** Add a new section to `CHANGELOG.md` with the version
number, date, and a summary of what changed. Group entries under `Added`, `Fixed`, and
`Changed` headings. The entries come directly from the squashed commit messages on `main`
since the last release.

**Step 3 — Commit the changelog.**

```bash
git checkout main
git pull
# Edit CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: release v0.2.0"
git push
```

**Step 4 — Tag the release.**

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

Pushing the tag triggers `deploy-prod.yml`, which builds the production images and fires
the production Dokploy webhooks.

**Step 5 — Monitor.** Watch application logs in Dokploy for the first 15–30 minutes
post-deploy. Check the `/health` endpoint on the production API. Verify a sample query
returns a valid cited response.

**Step 6 — Create a GitHub release.** From the repository's Releases page, create a
new release from the tag. Paste the changelog entries for this version into the release
notes. This creates a permanent record visible in the repository.

### Smoke Test Checklist

Run this checklist on the dev environment before cutting a release and on production
immediately after.

```
API Health
  [ ] GET /health returns {"status": "ok"} with all dependencies green
  [ ] Database, Qdrant, and Ollama all report "ok"

Authentication
  [ ] POST /auth/login with valid credentials returns JWT + refresh token
  [ ] Authenticated request to a protected endpoint succeeds
  [ ] Request without auth token returns 401

Query Pipeline
  [ ] POST /query with a known question returns a non-empty answer
  [ ] Response includes at least one citation with union, document, article, and section
  [ ] Response includes the legal disclaimer
  [ ] Nuclear keyword in query triggers correct retrieval (includes NPA)
  [ ] Cross-union comparison query routes to Sonnet (verify in query log model_used field)

Edge Cases
  [ ] POST /query for a topic not in any agreement returns graceful "not found" response
  [ ] POST /query with missing question field returns 400
  [ ] Rate-limited tenant returns 429 after exceeding limit

Corpus
  [ ] GET /documents returns expected document count with no ingestion errors flagged
```

### Rollback Procedure

If a production deploy introduces a regression, the rollback path is:

1. Identify the last known-good Git SHA from the GitHub Releases page or `git log --oneline`.
2. In Dokploy, update the `GIT_SHA` environment variable on the affected service to the
   known-good SHA.
3. Trigger a manual redeploy from the Dokploy dashboard — this pulls the previously built
   image for that SHA from GHCR.
4. Verify health endpoint and run smoke test.
5. Open a GitHub Issue documenting what broke, what the rollback was, and what needs to
   be fixed before re-deploying.

Because images are tagged with the Git SHA and retained in GHCR, any previous build is
immediately available for rollback without rebuilding. This is why `latest` tags alone
are insufficient — always deploy by SHA.

---

## 8. Incident Response

### Priority Order

When something breaks in production: **contain → communicate → diagnose → fix →
document**. Always in that order.

Contain first. If rollback is viable, do it before attempting a hotfix. A working old
version while you diagnose is far better than a broken new version while you debug under
pressure. The only exception is when the regression involves data corruption or a security
issue where the old version would make things worse.

### Hotfix Process

For urgent fixes that cannot wait for the normal `main → validate → tag` cycle:

```bash
# Branch from the current production tag, not from main
git checkout v0.2.0
git checkout -b fix/critical-citation-failure

# Make the fix
# ...

# Push and open a PR targeting main
git push origin fix/critical-citation-failure
```

After the hotfix merges to `main`, cut a PATCH release immediately (`v0.2.1`). Do not
leave hotfixed code in `main` without a corresponding release tag — it makes the
production state ambiguous.

### Incident Record

Every production incident gets a brief record in `docs/runbooks/incidents/`. The record
does not need to be long, but it must exist.

```markdown
# Incident: [Short description] — [Date]

## What broke
[One paragraph. What was the user-visible impact?]

## Timeline
- HH:MM — symptom first observed
- HH:MM — root cause identified
- HH:MM — rollback / fix deployed
- HH:MM — service confirmed healthy

## Root cause
[One to three sentences.]

## Fix
[What was changed. Link to the PR or commit.]

## Prevention
[One or two actions to prevent recurrence. Create GitHub Issues for each.]
```

---

## Appendix — Quick Reference

### Common Git Operations

```bash
# Start new work
git checkout main && git pull
git checkout -b feat/my-feature

# Keep branch up to date during development
git fetch origin
git rebase origin/main

# Push and open a PR
git push origin feat/my-feature
gh pr create --title "feat(rag): add nuclear context detection" --body-file /tmp/pr-body.md

# Cut a release
git checkout main && git pull
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### Conventional Commit Types at a Glance

```
feat      New feature
fix       Bug fix
chore     Maintenance, deps, config
docs      Documentation only
refactor  Code restructuring, no behaviour change
test      Adding or updating tests
perf      Performance improvement
ci        CI/CD pipeline changes
```

### Environment Variables — Where Each Service Reads Them

| Variable | Read By |
|---|---|
| `DATABASE_URL` | `epsca-api` |
| `QDRANT_URL` | `epsca-api` |
| `OLLAMA_URL` | `epsca-api`, `services/ingestion/` scripts |
| `ANTHROPIC_API_KEY` | `epsca-api` |
| `JWT_SECRET` | `epsca-api` |
| `NEXT_PUBLIC_API_URL` | `apps/web` (baked at build time) |
| `ENVIRONMENT` | `epsca-api` |
