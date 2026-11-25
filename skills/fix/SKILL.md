---
name: fix
description: >-
  Have arc's Fixer resolve open findings on the branch's local PR (created by
  `arc local-review` in `.arc/review.db`) — all findings, one file's findings,
  or a single finding — creating one commit per fix on the current branch. Use
  when the user says "fix #N", "fix the real issues", or "arc fix" after a
  local review. Edits code in the working tree and updates the local PR;
  pushes nothing.
allowed-tools: "Bash Read"
---

# arc fix

## 1. Preflight and check open findings
Follow `${CLAUDE_PLUGIN_ROOT}/reference/preflight.md` (the branch must already have an open local PR from `arc local-review`; no remote server is required).

The working tree must be clean (`git status --porcelain` must be empty — no uncommitted edits or untracked files). If it isn't, ask the user to commit, stash, or ignore their changes; never do it for them.

Next, preview the open findings and the Fixer's plan without editing anything:
```bash
arc fix --dry-run --json      # Fixer evaluates each finding [AGREE]/[DISAGREE] + plan; makes no edits
```
Always use the exact finding IDs returned; never invent one.

## 2. Pick the scope
| Goal | Command |
|---|---|
| Preview a fix plan only | `arc fix [<target>] --dry-run` |
| Fix one finding | `arc fix <number>` |
| Fix findings in a file or folder | `arc fix <path>` |
| Fix all open findings on the PR | `arc fix` |
| Fix only lines added against a base ref | `arc fix --base <ref>` |

How `arc fix` works (`arc fix --help`): the Fixer answers each finding (`fixed` or `wontfix`), edits the working tree, runs the checks in `presubmit.toml`, and creates one commit per fix on the current branch. The local reviewer then re-checks the changes in the same run, looping until LGTM or `[review] max_rounds` is reached.

Because `arc fix` commits directly to the user's branch, confirm with them before running a non-dry-run fix, and do not modify files while it is running.

## 3. Report what happened
Inspect `arc fix … --json` for `transitions` (how each finding was resolved), `open_issues`, `success`, and `error`. Show the transitions and the new commits (`git log -p refs/arc/before-fix/<branch>..HEAD`). If any finding remains open or `success` is `false`, report the exact error — never claim success on a non-zero exit.

## 4. Keep or undo the fixes
All fixes are committed on the current branch, and the pre-fix HEAD is saved at `refs/arc/before-fix/<branch>`. Pushing is an outward action — ask the user first:
```bash
git log --oneline refs/arc/before-fix/<branch>..HEAD   # review commits from this run
arc submit                                              # push and hand the branch to the pipeline's review
git reset --hard refs/arc/before-fix/<branch>           # undo the entire fix run
```
The pipeline's review results appear on the PR's review page (and arrive in your session if `arc bridge` is enabled).
