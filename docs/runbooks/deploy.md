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

The live site moved from `*.epscaxplor.boilerhaus.org` to `epscaxplor.com` (apex web) +
`api.epscaxplor.com` via a dual-domain transition on the same VPS. Order matters:

1. **DNS first.** Point `epscaxplor.com`, `www.epscaxplor.com`, and `api.epscaxplor.com`
   at the VPS (`149.202.56.68`, direct/un-proxied) and confirm they resolve
   (`dig +short <host>`) **before** deploying the new Traefik `Host` rules — Traefik's
   Let's Encrypt HTTP-01 challenge does **not** auto-retry on failure.
2. **Repo vars.** Set `PROD_API_URL`, `PROD_WEB_URL`, `SMOKE_API_URL` to the new hosts,
   right before the merge; freeze other `main` merges across this window (the `deploy-dev`
   verify would otherwise poll the not-yet-live host and fail).
3. **Merge the compose PR** → auto rebuild (`:latest`, new API origin baked in) + Dokploy
   redeploy + LE cert issuance for the new hosts.
4. **Dokploy env.** Set the `epsca-api` stack `CORS_ORIGINS` to `https://epscaxplor.com`
   and redeploy the API (the CORS middleware and the #104 CSRF Origin gate both read it).
5. **Verify** (new hosts): valid LE cert + the #146 security headers via `curl -sSI`,
   `/health` `git_sha` matches, `/docs` loads, browser login→refresh→logout round-trips,
   old host redirects to the apex, cross-site `Origin`→`/auth/refresh` still `403`.

**Cert stuck?** If a new host serves a default/self-signed cert (DNS raced the deploy),
`ssh boiler@149.202.56.68` and `docker restart dokploy-traefik` to force a fresh challenge
once DNS is correct, then re-`curl -sSI`.

The old `*.boilerhaus.org` hosts keep serving (API) / `302`-redirect (web) during a
~14-day dual-run, then a cleanup PR drops the old `Host` rules and flips `www`→apex to `301`.
