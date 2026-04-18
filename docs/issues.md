# EPSCAxplor — Issue Tracker

Local mirror of GitHub issues. Update this file as issues are completed.
All issues also exist at https://github.com/BoilerHAUS/EPSCAxplor/issues

**Legend:**
- `[ ]` open  `[x]` closed/done
- `[no-pr]` ops/config task, no pull request needed
- `[pr]` requires a feature branch and PR targeting `main`

---

## Phase 0 — Foundation

Goal: Running infrastructure, empty but functional services. Completion gate: `GET /health` returns `{"status":"ok"}` with all dependencies green.

| # | type | status | title |
|---|------|--------|-------|
| [#1](https://github.com/BoilerHAUS/EPSCAxplor/issues/1) | pr | [x] | chore(ci): commit deploy-dev.yml webhook error handling improvement |
| [#2](https://github.com/BoilerHAUS/EPSCAxplor/issues/2) | pr | [x] | chore(ci): add PR template and pull request workflow rules |
| [#3](https://github.com/BoilerHAUS/EPSCAxplor/issues/3) | no-pr | [x] | ops: configure GitHub Actions secrets for Dokploy deployment |
| [#4](https://github.com/BoilerHAUS/EPSCAxplor/issues/4) | no-pr | [x] | ops: create Dokploy apps on OVH VPS and capture webhook URLs |
| [#5](https://github.com/BoilerHAUS/EPSCAxplor/issues/5) | no-pr | [x] | ops: VPS cleanup — remove Nextcloud and Mistral 7B |
| [#6](https://github.com/BoilerHAUS/EPSCAxplor/issues/6) | no-pr | [x] | ops: pull nomic-embed-text into Ollama on VPS |
| [#7](https://github.com/BoilerHAUS/EPSCAxplor/issues/7) | pr | [x] | feat(infra): create Docker Compose production and dev stacks |
| [#8](https://github.com/BoilerHAUS/EPSCAxplor/issues/8) | pr | [x] | feat(db): create initial database migrations for all PostgreSQL tables |
| [#9](https://github.com/BoilerHAUS/EPSCAxplor/issues/9) | pr | [x] | feat(api): build FastAPI skeleton with /health endpoint |
| [#10](https://github.com/BoilerHAUS/EPSCAxplor/issues/10) | no-pr | [x] | ops: deploy epsca-db and epsca-qdrant containers on VPS |
| [#41](https://github.com/BoilerHAUS/EPSCAxplor/issues/41) | no-pr | [x] | ops: restore ollama-proxy nginx container for EPSCAxplor service connectivity |

---

## Phase 1 — Proof of Concept

Goal: End-to-end pipeline validated against 3 unions (IBEW Generation, Sheet Metal, United Association). Completion gate: correctness ≥ 85%, citation accuracy = 100%.

| # | type | status | title |
|---|------|--------|-------|
| [#11](https://github.com/BoilerHAUS/EPSCAxplor/issues/11) | pr | [x] | feat(ingestion): build download and extract pipeline stages |
| [#12](https://github.com/BoilerHAUS/EPSCAxplor/issues/12) | pr | [x] | feat(ingestion): build classify and chunk pipeline stages |
| [#13](https://github.com/BoilerHAUS/EPSCAxplor/issues/13) | pr | [x] | feat(ingestion): build embed, store, and pipeline orchestrator |
| [#14](https://github.com/BoilerHAUS/EPSCAxplor/issues/14) | no-pr | [x] | ops: run Phase 1 POC ingestion (IBEW Generation, Sheet Metal, UA) |
| [#15](https://github.com/BoilerHAUS/EPSCAxplor/issues/15) | pr | [x] | feat(rag): implement query pre-processing (nuclear detection, union/scope detection) |
| [#16](https://github.com/BoilerHAUS/EPSCAxplor/issues/16) | pr | [x] | feat(rag): implement Qdrant filtered similarity search and context assembly |
| [#17](https://github.com/BoilerHAUS/EPSCAxplor/issues/17) | pr | [x] | feat(api): implement POST /query endpoint with model routing and response structure |
| [#18](https://github.com/BoilerHAUS/EPSCAxplor/issues/18) | no-pr | [ ] | ops: evaluate Phase 1 POC against gold question set |
| [#39](https://github.com/BoilerHAUS/EPSCAxplor/issues/39) | pr | [x] | chore(ci): extract shared validation steps into reusable workflow |
| [#51](https://github.com/BoilerHAUS/EPSCAxplor/issues/51) | pr | [x] | feat(ingestion): add wage_schedule entries to corpus_manifest for Phase 1 POC unions |
| [#53](https://github.com/BoilerHAUS/EPSCAxplor/issues/53) | pr | [x] | feat(ingestion): convert PDFs to markdown before chunking for accurate table extraction |

---

## Phase 2 — Full Corpus

Goal: All 58 documents ingested and queryable. Completion gate: full gold question set passes at Phase 1 thresholds.

| # | type | status | title |
|---|------|--------|-------|
| [#19](https://github.com/BoilerHAUS/EPSCAxplor/issues/19) | pr | [ ] | feat(ingestion): expand corpus_manifest.yaml for all 18 unions |
| [#20](https://github.com/BoilerHAUS/EPSCAxplor/issues/20) | no-pr | [ ] | ops: run full corpus ingestion (all 58 documents) |
| [#21](https://github.com/BoilerHAUS/EPSCAxplor/issues/21) | pr | [ ] | feat(ingestion): validate and refine chunking for wage schedule table extraction |
| [#22](https://github.com/BoilerHAUS/EPSCAxplor/issues/22) | no-pr | [ ] | ops: evaluate full corpus against complete gold question set |

---

## Phase 3 — Product Layer

Goal: Secure, multi-tenant product ready for beta users.

| # | type | status | title |
|---|------|--------|-------|
| [#23](https://github.com/BoilerHAUS/EPSCAxplor/issues/23) | pr | [ ] | feat(auth): implement JWT authentication with refresh token rotation |
| [#24](https://github.com/BoilerHAUS/EPSCAxplor/issues/24) | pr | [ ] | feat(auth): implement API key authentication for enterprise tier |
| [#25](https://github.com/BoilerHAUS/EPSCAxplor/issues/25) | pr | [ ] | feat(api): implement subscription tier enforcement and rate limiting |
| [#26](https://github.com/BoilerHAUS/EPSCAxplor/issues/26) | pr | [ ] | feat(api): implement GET /documents and GET /query-history endpoints |
| [#27](https://github.com/BoilerHAUS/EPSCAxplor/issues/27) | pr | [ ] | feat(web): build Next.js frontend skeleton and API client |
| [#28](https://github.com/BoilerHAUS/EPSCAxplor/issues/28) | pr | [ ] | feat(web): build chat interface with query submission and citation display |
| [#29](https://github.com/BoilerHAUS/EPSCAxplor/issues/29) | pr | [ ] | feat(web): build corpus browser UI (document list and search) |
| [#30](https://github.com/BoilerHAUS/EPSCAxplor/issues/30) | pr | [ ] | feat(web): build query history UI |
| [#31](https://github.com/BoilerHAUS/EPSCAxplor/issues/31) | no-pr | [ ] | ops: Phase 3 smoke test — multi-tenant isolation and rate limiting verification |
| [#40](https://github.com/BoilerHAUS/EPSCAxplor/issues/40) | pr | [ ] | chore(ci): create deploy-prod.yml workflow for version tag deploys |

---

## Phase 4 — Go to Market

Goal: Paid product with billing and white-label capability.

| # | type | status | title |
|---|------|--------|-------|
| [#32](https://github.com/BoilerHAUS/EPSCAxplor/issues/32) | pr | [ ] | feat(api): Stripe subscription integration |
| [#33](https://github.com/BoilerHAUS/EPSCAxplor/issues/33) | pr | [ ] | feat(web): build pricing page and Stripe checkout flow |
| [#34](https://github.com/BoilerHAUS/EPSCAxplor/issues/34) | pr | [ ] | feat(infra): white-label tenant configuration via Traefik custom domain routing |
| [#35](https://github.com/BoilerHAUS/EPSCAxplor/issues/35) | pr | [ ] | feat(web): build enterprise API key management dashboard |
| [#36](https://github.com/BoilerHAUS/EPSCAxplor/issues/36) | no-pr | [ ] | ops: confirm EPSCA document usage rights before public launch |
| [#37](https://github.com/BoilerHAUS/EPSCAxplor/issues/37) | no-pr | [ ] | ops: register production domain and update Traefik routing |
| [#38](https://github.com/BoilerHAUS/EPSCAxplor/issues/38) | pr | [ ] | feat(web): build marketing site and add terms of service / privacy policy |

---

## How to use this file

1. At the start of each session, read `docs/issues.md` to find the first open `[ ]` item in the current phase.
2. Work the issue. When done, mark it `[x]` and close it on GitHub: `gh issue close N`.
3. If a new issue is created mid-session, add it to the correct phase table here.
4. The phases are sequential gates — don't start Phase 2 work until Phase 1's completion criteria are met.
