# Review on the pipeline

On the pipeline, a change is reviewed by the **review service**, not on your machine: `arc submit` hands it over, reviewer agents file findings, the author answers each one, the new head is reviewed again, and when every reviewer says LGTM the service grants a **pass** for that exact commit. Only a pass that matches the PR's head lets the merge machine take it ([Merge](merge-gate.md)).

## 1. Hand it to review: `arc submit`

```bash
arc submit                      # a new PR: push, open it, queue its review
arc submit --pr 514             # this head as an update of PR 514
```

Before anything is pushed, `presubmit.toml`'s checks run on HEAD ([Configuration](configuration.md#repopresubmittoml--the-checks-before-submit)). Every check runs and a failed one stops nothing: the head is pushed, each check's result is pushed beside it as a git note (shown on the PR's page and the board), the PR goes to review, the failed checks are named and arc exits 11. `arc submit` pushes the branch under its own name (never over commits the remote has and HEAD lacks), opens or reuses its PR, puts the update on the review queue, and exits:

```
[A.R.C.] submit: PR #514 · handed to review (<sha>)
         <url>
         branch <branch> — the review service asks the reviewers the tenant's routes name; their LGTM grants the pass and the merger lands it. A new push is a new version and is reviewed again
```

- Run inside an agent session with the bridge on, it also registers the PR to that session (`bridge: verdicts for this PR go to <name> in channel pr:…`), so the review comes back to you ([Team up](bridge.md)).
- `--branch <name>` asserts which branch this is for and refuses if HEAD is elsewhere — use it when something else may move HEAD.
- `--after <N>` lands this change only after PR N has landed.
- A `b/<n>` in the PR title lists this submission on that board issue; a `b/<n>` that does not exist exits 8.

## 2. Who reviews

The repo's routes in `~/.arc/machine.toml` on the pipeline's machine name the reviewers ([Configuration](configuration.md#arcmachinetoml--the-pipeline-machine)):

```toml machine.toml#tenant
[[tenant.review.route]]          # PRs labelled arc-bypass: the dummy reviewer, which says LGTM
label    = "arc-bypass"
reviewer = "dummy"
name     = "dummy"

[[tenant.review.route]]          # every other PR: a real reviewer
reviewer = "react"
name     = "react"
```

- `reviewer` is `dummy` (says LGTM to everything), `basic` or `react`; real reviewers use the `[roles]` in the tenant clone's own `.arc/config.toml`. `name` is whose name the replies carry.
- **With no route, nobody reviews and nothing lands.** A repo nobody else reviews routes every PR to `dummy`.
- `[tenant.review] gate` says which LGTMs grant the pass: `all_lgtm` (default, every reviewer of the head) or `one_lgtm`.
- `[tenant.review] max_rounds` (default 5) is how many rounds a reviewer may go without an LGTM; once it has used them, it lets that head through and stops reviewing.
- `arc submit --bypass-review` labels the PR `arc-bypass`, which these routes hand to the dummy reviewer. Even a skipped review goes through the service and stays on the record.

## 3. Findings come back

Each round's result is written to `refs/arc/reports/<cl>`. With the bridge on, a review with findings is a letter in the PR's channel, put into your session when it stops (or waking it): the findings, and an `arc submit --pr <N> --fix-answers -` command to fill in.

## 4. Answer each finding

Every finding is answered **fixed** (with what changed) or **won't fix** (with why). Push the fix first, then:

```bash
arc submit --pr 514 --fix-answers - <<'EOF'
[{"finding": 3, "kind": "fixed", "text": "carried the error typed: #[from] GitError"},
 {"finding": 5, "kind": "wontfix", "text": "the empty string is the wire format the client expects"}]
EOF
```

The answers go with that head as one update, in the array's order. One bad item refuses them all and nothing is sent; `--fix-answers` without `--pr` is refused. Or let the Fixer do it on your machine — `arc local-review`, then `arc fix` ([The commands](commands.md)) — and hand the new head over with `arc submit --pr <N>`.

The reviewer then reads the new head: it closes an answered finding or reopens it, and may raise new ones. A new push is a new version, reviewed again.

## 5. LGTM and the pass

When the reviewers the routes asked for have said LGTM on the head, the review service grants the pass: `refs/arc/pass/<pr>`, bound to that commit. The merge machine admits only a PR whose pass is its head.

- **To keep a PR from landing, label it `arc-hold`.** The merger skips a held PR even when it has a pass; take the label off and it is taken again.
- **To end a PR without landing it**, run `arc submit --abandon "<why>"` on its branch (alone — it takes no other flag): the close, with your reason verbatim, goes on the review queue, then the PR is closed on GitHub. It pushes and opens nothing. Do not close the PR by hand.

## 6. People on the review board

The board (arc-web) has a **Review** tab: the changes that need you and why, what the agents are working through, and the history.

- **The change page** — what the change is (title, status, author, size), why it waits, each reviewer's opinion with its findings, the head's files, the revision history, its risk and blast radius, and the head's presubmit checks. Its buttons: *Open on GitHub*, *Fix again* (send it back to its author) and *LGTM*.
- **Files · comments** — the editor page: one version's code and its findings on one bench, diffing any version against any later one. Select lines and comment on them from the context menu; the comment is a finding of your round. Rule on a finding (close it, or send it back), then *Send review* sends your whole round at once. Nobody lands a change from this page — that is the merge machine's.

---

*Next: [Merge](merge-gate.md) · [Team up](bridge.md) · [Releases and deploys](release.md).*
