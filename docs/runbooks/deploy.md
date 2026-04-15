# Runbook: Deployment

## Dev Deploy (automatic)

Every merge to `main` triggers `deploy-dev.yml`:
1. Validates API (ruff, mypy, pytest) and Web (tsc, eslint)
2. Builds and pushes Docker images to GHCR tagged with Git SHA
3. Fires Dokploy webhooks to redeploy `epsca-api` and `epsca-web`

## Production Release

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
