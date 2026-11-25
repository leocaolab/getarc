---
name: automate
description: >-
  Set up A.R.C. (arc) to run automatically — either reviewing every commit via
  a git post-commit hook or gating PR merges via merge.yml. Use when the user
  wants arc to run unattended ("run arc on every commit", "gate merges on arc",
  "自动跑 arc").
allowed-tools: "Bash Read Edit"
---

# arc automation

## 1. Preflight
Follow `${CLAUDE_PLUGIN_ROOT}/reference/preflight.md`.

## 2. Choose a mechanism (confirm with the user before modifying the repo)

**A) Review every commit — git `post-commit` hook**
```bash
arc hook install       # runs `arc local-review` in the background after each commit; logs to .arc/critic.log
arc hook uninstall     # remove the hook
```
- The hook runs `arc local-review` against the clone's own `.arc/review.db` — no remote server or GitHub PR needed. If `arc local-review` cannot start (e.g., missing critic role or unreadable `.arc/review.db`), it skips the review and prints the reason in the terminal.
- It automatically skips commits made in linked worktrees, during rebases or cherry-picks, on `--amend`, and commits that were already reviewed (see `docs/user-guide/coding-agents.md`).
- It refuses to overwrite an existing hook it didn't create; `--force` only replaces an older arc hook.
- The hook is read-only: it never edits or commits code. To apply fixes, run `arc fix`.

**B) Gate every merge — `.github/workflows/merge.yml`**
In the team edition, a self-hosted merge runner executes `.github/workflows/merge.yml` on both the base branch and the merged tree, landing the PR only if it introduces no new failures. Writing and validating this file is stage 5 of **`arc-skills:arc-setup`** (see `docs/user-guide/merge-gate.md`, and validate jobs with `arc workflow .github/workflows/merge.yml --job <job> --list`). Note that the merge server itself is operator-hosted and not publicly released.

## 3. What automation does not do
`arc` has no built-in cron scheduler, and GitHub Actions never triggers `merge.yml` (its only trigger is `workflow_dispatch`). Also remember that `arc local-review` exits `0` even when it finds issues — any unattended script gating on findings must inspect `--json` (see `preflight.md`).
