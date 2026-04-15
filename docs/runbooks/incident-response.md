# Runbook: Incident Response

## Priority Order

**Contain → Communicate → Diagnose → Fix → Document**

Rollback first if viable. A working old version while you diagnose is far better
than a broken new version while you debug under pressure.

## Hotfix Process

```bash
# Branch from the production tag, not from main
git checkout vX.Y.Z
git checkout -b fix/description-of-fix
# Make the fix, then push and open a PR targeting main
git push origin fix/description-of-fix
# After merge, cut a PATCH release immediately
```

## Incident Record Template

Create a file in `docs/runbooks/incidents/YYYY-MM-DD-short-description.md`:

```markdown
# Incident: [Short description] — [Date]

## What broke
[User-visible impact]

## Timeline
- HH:MM — symptom first observed
- HH:MM — root cause identified
- HH:MM — rollback / fix deployed
- HH:MM — service confirmed healthy

## Root cause
[One to three sentences.]

## Fix
[What changed. Link to PR or commit.]

## Prevention
[Actions to prevent recurrence. Create GitHub Issues for each.]
```
