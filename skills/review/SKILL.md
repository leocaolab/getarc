---
name: review
description: >-
  Run an A.R.C. (arc) local review of the branch's PR and present the REAL findings
  first — triaged into CORE vs noise, not a raw dump. Use when the user asks to review
  their changes, a file, a folder, a commit or the whole PR ("review my changes",
  "arc local-review this", "评一下"). Read-only: it files findings as a reviewer reply
  on the PR and never edits code.
allowed-tools: "Bash Read"
---

# arc local-review (with triage)

## 1. Preflight
Follow `${CLAUDE_PLUGIN_ROOT}/reference/preflight.md`. `arc local-review` needs no review
service and no PR: it is a self-check on this clone, its findings go to a local PR in
`.arc/review.db`. It refuses on the default branch or a detached HEAD — say so and stop; do
not fabricate a result.

## 2. Scope
| The person means | Command |
|---|---|
| "my changes" / this branch / uncommitted work | `arc local-review` |
| the structure (god-modules, duplication) | `arc rot` → **`arc-skills:rot`** |

`arc local-review` takes no scope flag: it always reviews the branch's whole change against
the remote's default branch, the working tree as it is (a dirty tree through a commit of it
that moves nothing). One commit or one file alone cannot be asked for.

## 3. Run, then read the result honestly
```bash
arc --json local-review
```
Read the exit code and the envelope by the table in `preflight.md`. Exit 0 means the
review ran and its reply went to the local PR — not that the code is clean.

## 4. Triage
Follow `${CLAUDE_PLUGIN_ROOT}/reference/triage.md`: present CORE first, fold the rest.

## 5. Next
Offer: fix which (→ **`arc-skills:fix`**), or fix them yourself in the working tree and run
`arc local-review` again. When the person is done, they push with `git push`. In the team
edition, a PR under review takes the answers with the update
(`arc submit --pr <N> --fix-answers -`, JSON on stdin: each `{"finding": <n>, "kind": "fixed"|"wontfix", "text": "…"}`)
— `arc submit` pushes, so ask first.
