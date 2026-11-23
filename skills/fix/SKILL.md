---
name: fix
description: >-
  Have arc's Fixer answer the findings the branch's local PR owes (the one `arc local-review`
  opened in `.arc/review.db`) — every one, a file's, or one finding — each fix one commit on
  the current branch. Use when the user says "fix #N" / "fix the real issues" / "arc fix"
  after a local review. It edits code in the working tree and sends the answers as the
  local PR author's update, handled on this clone; it pushes nothing.
allowed-tools: "Bash Read"
---

# arc fix

## 1. Preflight + know the targets
Follow `${CLAUDE_PLUGIN_ROOT}/reference/preflight.md` (the branch must hold an open local PR:
run `arc local-review` first; no review service is needed). The working tree must be HEAD's —
no tracked change and no untracked file (`git status --porcelain` prints nothing); ask the
person to commit, stash or ignore what is there, never do it for them. Then see what is owed — read-only:
```bash
arc fix --dry-run --json      # the Fixer assesses each finding [AGREE]/[DISAGREE] + a plan; changes nothing
```
Use the finding numbers it names; never invent one.

## 2. Pick the scope
| The person wants | Command |
|---|---|
| a plan only | `arc fix [<target>] --dry-run` |
| one finding | `arc fix <number>` |
| a file or folder's findings | `arc fix <path>` |
| every finding the PR owes | `arc fix` |
| the PR's added lines against a base | `arc fix --base <ref>` |

What it does (`arc fix --help`): the Fixer answers each finding `fixed` or `wontfix`,
editing the working tree; each fix is one commit on the current branch, on top of the one
before; the answers go to the local PR as the author's update, and the local reviewer
re-checks them in the same run; while that review leaves findings it fixes again, until the
reviewer says LGTM or has taken its `[review] max_rounds` turns, and the last line says which. The Fixer is told to run the checks of the repo's `presubmit.toml`. It commits on the person's branch — confirm with them
before running a non-dry-run fix, and do not touch the tree while it runs.

## 3. Report what happened
Read `arc fix … --json`: `transitions` (what this run's answers did to each finding),
`open_issues`, `success`, `error`. Show the transitions and the run's commits
(`git log -p refs/arc/before-fix/<branch>..HEAD`). If a finding is still open or the
envelope says `success: false`, say so with its error — never claim success on a
non-zero exit.

## 4. Keeping or undoing the fixes
The fixes are already on the branch. Where it was before the run is kept as
`refs/arc/before-fix/<branch>`, and the run prints the undo command. Pushing is outward —
ask first:
```bash
git log --oneline refs/arc/before-fix/<branch>..HEAD   # this run's fixes
git push                                                # personal edition: the person pushes
git push && arc submit                                  # team edition: the review service reviews the new head
git reset --hard refs/arc/before-fix/<branch>           # or: undo the whole run
```
In the team edition the review's result comes back on the PR's review page (and, with the
bridge on, into the session).
