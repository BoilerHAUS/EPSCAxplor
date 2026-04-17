# EPSCAxplor

RAG-powered SaaS for querying EPSCA collective agreements (Ontario, Canada).
Deployed on OVH VPS via Docker / Dokploy + Traefik. Solo developer, AI-assisted.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript |
| Backend | FastAPI (Python 3.12), Pydantic Settings |
| Database | PostgreSQL 16 (`epsca-db`) |
| Vector store | Qdrant (`epsca-qdrant`) |
| Embeddings | nomic-embed-text via Ollama (768 dims, local) |
| Generation | Claude Haiku (standard queries), Claude Sonnet (cross-union comparisons) |
| Deployment | Docker Compose, Dokploy, Traefik v3, GHCR |

## Non-Negotiable Answer Requirements

Every response from the query pipeline must be **grounded, cited, versioned, and disclaimed**.
Answers sourced from model inference rather than retrieved documents are pipeline failures.

## Key Architecture Constraints

- Nuclear site queries (Darlington / Pickering / Bruce Power / OPG) must widen retrieval to include NPA docs alongside the primary CA.
- Vector dimensions are fixed at **768** — must be consistent across ingestion and Qdrant collection config.
- Prompt caching is enabled on all Claude API calls; the system prompt is the cache anchor.
- Squash-merge only; PR title = canonical commit message (Conventional Commits format).

## Monorepo Lanes

| Lane | Blast Radius | Notes |
|---|---|---|
| `apps/` | Contained | Broken frontend doesn't affect API |
| `services/` | High | API/ingestion bugs affect all users |
| `infra/` | Highest | Misconfigured Traefik/Compose can down everything |
| `docs/` | None | |

Cross-lane PRs require explicit justification.

## Local Development Notes

### Testing migrations locally

`dokploy-network` is an **external** network — `docker compose up` will fail locally
because that network only exists on the VPS. Do not try to bring up the full stack locally.

For migration testing, spin up a standalone throwaway postgres container with no port
binding (ports 5432–5434 are likely occupied by other projects) and access it via
`docker exec`:

```bash
docker run -d --name epsca-db-test \
  -e POSTGRES_DB=epsca \
  -e POSTGRES_USER=epsca_user \
  -e POSTGRES_PASSWORD=testpassword \
  postgres:16-alpine

# Apply migrations
for f in $(ls infra/db/migrations/*.sql | sort); do
  docker exec -i epsca-db-test psql -U epsca_user -d epsca < "$f"
done

# Run queries
docker exec -i epsca-db-test psql -U epsca_user -d epsca <<'SQL'
-- your SQL here
SQL

# Teardown
docker rm -f epsca-db-test
```

## Github Issues

Issues are tracked at [BoilerHAUS/EPSCAxplor](https://github.com/BoilerHAUS/EPSCAxplor/issues) and mirrored locally in [docs/issues.md](docs/issues.md).

**Workflow:**
- Issues are grouped by phase with `[ ]` open and `[x]` closed status.
- `[no-pr]` items are ops/config tasks; `[pr]` items require a feature branch and PR targeting `main`.
- Phases are sequential — do not start Phase N+1 until Phase N's completion gate is met.

**When starting a session:** Read `docs/issues.md` to find the current phase and the first open `[ ]` item.

**When an issue is opened:** Add it to the correct phase table in `docs/issues.md` with `[ ]` status and the appropriate `[pr]` or `[no-pr]` type.

**When an issue is closed:** Mark it `[x]` in `docs/issues.md`. If not already closed on GitHub, run `gh issue close N`.

**On request ("review issues" / "sync issues"):** Run `gh issue list --state all --limit 100` and reconcile `docs/issues.md` with the live GitHub state — mark any manually-closed issues `[x]`, add any issues missing from the runbook, and remove entries for issues that no longer exist.

## Reference Docs

- Architecture & data model: [docs/planning.md](docs/planning.md)
- Branch strategy, CI/CD, release, rollback: [docs/github-workflow.md](docs/github-workflow.md)

## Agents — Use for This Project

| Agent | When |
|---|---|
| `python-reviewer` | After writing any FastAPI / Python code |
| `typescript-reviewer` | After writing any Next.js / TypeScript code |
| `database-reviewer` | When writing SQL, migrations, or Qdrant schema changes |
| `security-reviewer` | Before commits touching auth, JWT, or API keys |
| `tdd-guide` | New features and bug fixes — write tests first |
| `planner` | Before implementing any new feature |
| `build-error-resolver` | When builds fail |

## MCP — Useful for This Project

- **context7** (`/docs` skill) — FastAPI, Next.js, Qdrant, Anthropic SDK docs

## MCP — Not Relevant

Figma, Vercel, PubMed, Gmail, Google Calendar, Indeed, Jam, Excalidraw, Mermaid Chart.
Do not invoke these for this project.

## Token Efficiency

- Use the token efficiency skill located in .claude's skills directory for general token savings.
- Use the markdown-token-optimizer skill on all project markdown files
- Use caveman skill in lite mode