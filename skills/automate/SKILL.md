---
name: automate
description: >-
  Set up A.R.C. (arc) to run without being asked — a review of every commit (git
  post-commit hook) or a merge gate that decides every landing (merge.yml). Use when
  the user wants arc to run unattended ("run arc on every commit", "gate merges on
  arc", "自动跑 arc").
allowed-tools: "Bash Read Edit"
---

# arc automation

## 1. Preflight
Follow `${CLAUDE_PLUGIN_ROOT}/reference/preflight.md`.

## 2. Pick the mechanism (each changes the repo — confirm first)

**A) Every commit — the post-commit hook.**
```bash
arc hook install       # after each commit, in the background: arc local-review (the branch's change), logged to .arc/critic.log
arc hook uninstall     # remove it
```
- It runs `arc local-review`, which reviews on the clone's own `.arc/review.db` — no review
  service and no PR needed; a branch with no local PR yet gets one. When `arc local-review`
  could not start here (no critic role, an unreadable `.arc/review.db`) it reviews nothing
  and says why in the terminal (`… could not decide, so no review — …`).
- It skips commits made in a linked worktree, during a rebase or cherry-pick, on an
  amend, and commits already reviewed (`docs/user-guide/coding-agents.md`).
- It refuses to overwrite a hook it did not write; `--force` replaces only its own.
- The hook only reviews: it never edits or commits. Fixing is `arc fix`, run by a person.

**B) Every landing — the merge gate.** A merge machine runs
`.github/workflows/merge.yml` on the base and on the merged tree and lands a PR that
adds no new failure. Writing and checking that file is stage 5 of
**`arc-skills:arc-setup`** (rules: `docs/user-guide/merge-gate.md`; check each job with
`arc workflow .github/workflows/merge.yml --job <job> --list`). The merge machine itself
is an operator's and is not publicly released — say so.

## 3. What is not automation here
arc has no scheduler. GitHub never runs `merge.yml` (its only trigger is
`workflow_dispatch`). A review's exit 0 means it ran, not that the code is clean — an
unattended job that gates on findings reads them from `--json` (`preflight.md`).
