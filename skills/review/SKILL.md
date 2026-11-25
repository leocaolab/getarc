---
name: review
description: >-
  Run an A.R.C. (arc) local review of the current branch and present the real
  findings first — triaged into CORE vs. noise instead of a raw dump. Use when
  the user asks to review their changes, a file, a folder, a commit, or the PR
  ("review my changes", "arc local-review this", "评一下"). Read-only: it logs
  findings to the local PR record and never edits code.
allowed-tools: "Bash Read"
---

# arc local-review (with triage)

## 1. Preflight
Follow `${CLAUDE_PLUGIN_ROOT}/reference/preflight.md`. `arc local-review` needs no remote server or GitHub PR — it runs locally and writes findings to `.arc/review.db`. Note that it refuses to run on the default branch or a detached HEAD; if you're on one, tell the user and stop (never fabricate a review).

## 2. Scope
| User request | Command |
|---|---|
| "my changes" / this branch / uncommitted work | `arc local-review` |
| Whole-repo structure (god-modules, duplication) | `arc rot` → **`arc-skills:rot`** |

`arc local-review` has no file or commit filter: it always reviews the entire branch diff against the remote's default branch, including any uncommitted working-tree changes. Make sure the user knows it covers the whole branch, not just a single file or commit.

## 3. Run and inspect the result
```bash
arc --json local-review
```
Check both the exit code and the JSON envelope per `preflight.md`. Exit code `0` means the review completed and saved findings — **not** that the code is clean.

## 4. Triage
Follow `${CLAUDE_PLUGIN_ROOT}/reference/triage.md` to surface CORE findings first and collapse low-signal noise.

## 5. Next steps
Offer to fix specific findings via **`arc-skills:fix`**, or let the user edit the code themselves and re-run `arc local-review`. When ready, they can push with `git push`.

In the team edition, an open PR under review accepts fix answers via:
`arc submit --pr <N> --fix-answers -` (passing JSON on stdin: `{"finding": <n>, "kind": "fixed"|"wontfix", "text": "…"}`). Since `arc submit` pushes to the remote, always ask the user first.
