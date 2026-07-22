# Runbook: Deployment

## Dev Deploy (automatic)

Every merge to `main` triggers `deploy-dev.yml`:
1. Validates API (ruff, mypy, pytest) and Web (tsc, eslint)
2. Builds and pushes Docker images to GHCR tagged with Git SHA (the API image
   bakes the SHA in as `GIT_SHA`, surfaced at `/health`)
3. Fires Dokploy webhooks to redeploy `epsca-api` and `epsca-web`
4. **Verifies the deploy shipped**: polls `PROD_API_URL/health` until its
   `git_sha` matches the built commit (fails after ~5 min), then polls
   `PROD_WEB_URL` for HTTP 200 (skipped with a warning if that variable is
   unset). A stale container the webhook failed to update now fails the run
   instead of passing silently.

## Production Release

Pushing a `vX.Y.Z` tag triggers `deploy-prod.yml`:
1. Validates API (ruff, mypy) and Web (tsc, eslint)
2. Builds and pushes Docker images to GHCR, tagged with both the Git SHA and the version tag
3. Fires the prod Dokploy webhooks to redeploy `epsca-api` and `epsca-web`
4. **Verifies the release**: polls `PROD_API_URL/health` for up to ~5 minutes and fails the
   run if the API does not report healthy (200 = database + Qdrant + Ollama all `ok`). A green
   `deploy-prod` run therefore means the new release is actually live and healthy, not just
   that Dokploy accepted the webhook.

Only one production deploy runs at a time (`concurrency: deploy-prod`); overlapping tag
pushes queue rather than race.

See [github-workflow.md](../github-workflow.md#7-release-management) for the full release process.

```bash
# After verifying dev environment is healthy:
git checkout main && git pull
# Edit CHANGELOG.md with new version entries
git add CHANGELOG.md
git commit -m "chore: release vX.Y.Z"
git push
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

If the `Verify Production Health` job fails, the images are already in GHCR — follow the
Rollback steps below to pin the previous known-good SHA while you investigate.

## Rollback

1. Find last known-good SHA in GitHub Releases or `git log --oneline`
2. In Dokploy: update `GIT_SHA` env var on affected service to the good SHA
3. Trigger manual redeploy from Dokploy dashboard
4. Verify `/health` endpoint and run smoke test checklist

## GitHub Actions Secrets Required

| Secret | Purpose |
|---|---|
| `DOKPLOY_TOKEN` | Dokploy API token |
| `DOKPLOY_WEBHOOK_API` | Dev webhook for epsca-api |
| `DOKPLOY_WEBHOOK_WEB` | Dev webhook for epsca-web |
| `DOKPLOY_PROD_WEBHOOK_API` | Prod webhook for epsca-api |
| `DOKPLOY_PROD_WEBHOOK_WEB` | Prod webhook for epsca-web |

## GitHub Actions Variables Required

| Variable | Purpose |
|---|---|
| `PROD_API_URL` | Base URL of the production API (`https://api.epscaxplor.com`), polled by the post-deploy health check **and baked into the web bundle at build time** as `NEXT_PUBLIC_API_URL`. Update it *before* the merge that rebuilds `:latest`. A repository **variable**, not a secret — the URL is public. |
| `PROD_WEB_URL` | Base URL of the deployed web app (`https://epscaxplor.com`), polled for HTTP 200 after the web redeploy. Optional — if unset, the web readiness check is skipped with a warning. Repository **variable**, not a secret. |
| `SMOKE_API_URL` | Base URL the nightly smoke eval targets (`https://api.epscaxplor.com`). Optional — falls back to the same default hard-coded in `nightly-smoke.yml`. Repository **variable**, not a secret. |

## Domain migration (#152 — epscaxplor.com)

The live site moved to `epscaxplor.com` (apex web) + `api.epscaxplor.com` on the same VPS.
**Routing is managed by Dokploy's per-service Domains UI, not the `traefik.*` labels in
`docker-compose.yml` — Dokploy ignores those.** Order matters:

1. **DNS first.** Point `epscaxplor.com`, `www.epscaxplor.com`, `api.epscaxplor.com` at the
   VPS (`149.202.56.68`, direct/un-proxied) and confirm they resolve (`dig +short <host>`)
   **before** adding the domains in Dokploy — the Let's Encrypt HTTP-01 challenge fires when
   a domain is added and does **not** auto-retry on failure.
   - Namecheap gotcha: the **Host** field takes the short label (`@`, `api`, `www`), not the
     FQDN — entering the full domain builds `epscaxplor.com.epscaxplor.com` and nothing resolves.
2. **Add the domains in Dokploy** (each service → Domains → Add Domain): `api.epscaxplor.com`
   → epsca-api :8000; `epscaxplor.com` + `www.epscaxplor.com` → epsca-web :3000; HTTPS, cert
   `letsencrypt`. Dokploy creates the routers and auto-issues the certs. Confirm each with
   `curl -sSI https://<host>` (valid cert, HTTP 200).
3. **Repo vars + CORS.** Set repo variables `PROD_API_URL=https://api.epscaxplor.com`,
   `PROD_WEB_URL=https://epscaxplor.com`, `SMOKE_API_URL=https://api.epscaxplor.com`, and the
   Dokploy `epsca-api` env `CORS_ORIGINS=https://epscaxplor.com` (the CORS middleware and the
   #104 CSRF gate read it). `PROD_API_URL` is **baked into the web bundle** at build time.
4. **Merge to `main`** → `deploy-dev` rebuilds `:latest` with the new API origin baked in and
   redeploys; its verify polls `api.epscaxplor.com/health` (git_sha) + `epscaxplor.com` (200).
   Freeze other `main` merges from when the repo vars change until this lands.
5. **Verify:** `curl -sSI` the new hosts (valid cert), `/health` git_sha matches, `/docs`
   loads, browser login→refresh→logout round-trips (same-site cookie), cross-site
   `Origin`→`/auth/refresh` still `403`.
6. **Retire the old domains:** once the new domain is verified, remove
   `epscaxplor.boilerhaus.org` and `api.epscaxplor.boilerhaus.org` from Dokploy (they were a
   placeholder — no redirect kept).

**Cert stuck?** If a host serves a default cert (DNS raced the add), `ssh boiler@149.202.56.68`
then `docker restart dokploy-traefik` to force a fresh challenge, and re-`curl -sSI`.

**Security headers:** must be added via a Dokploy Traefik middleware, **not** compose labels
(Dokploy ignores `traefik.*` labels) — tracked separately.
