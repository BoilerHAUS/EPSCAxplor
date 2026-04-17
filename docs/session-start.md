# EPSCAxplor — Session Starter Prompt

Copy and paste the block below to start a new working session.

---

```
I'm working on EPSCAxplor, a RAG-powered SaaS for querying EPSCA collective agreements.
Read docs/issues.md to find the first open [ ] issue in the current phase.
Read docs/planning.md for architecture and requirements context.
Read CLAUDE.md for project constraints.

Rules for this session:
- All code changes go on a feature branch — never commit directly to main
- Every PR must reference a GitHub issue (Closes #N in the PR body)
- Branch naming: feat/, fix/, chore/, docs/ prefix + kebab-case description
- After writing code: run the python-reviewer or typescript-reviewer agent
- After writing any auth/API code: run the security-reviewer agent
- Mark issues [x] in docs/issues.md and run `gh issue close N` when done

Start by reading docs/issues.md and telling me which issue you're picking up and why.
```

---

## Notes

- If you want to target a specific issue, append: `Work on issue #N.`
- If multiple issues in a phase are unblocked, the agent will pick the most logical starting point.
- The `[no-pr]` issues (ops/config tasks) can be done in parallel with PR issues — flag them when you complete them manually so the doc stays accurate.
- be efficient, follow token efficiency guidelines in CLAUDE.md
